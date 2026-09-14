use caiman_terminal::{
    command_validation::Host,
    context::{CommandRecord, Session},
    guidance,
    host::{self, Response},
    worker::{self, Request},
};
use std::sync::{atomic::AtomicU64, Arc};
fn request(text: &str, input: &str) -> Request {
    let mut session = Session::new(1, "/tmp".into());
    session.at_prompt = true;
    session.input = input.into();
    Request {
        session,
        text: text.into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: true,
    }
}
fn failed(req: &mut Request, command: &str) {
    req.session.record(CommandRecord {
        command: command.into(),
        cwd: "/tmp".into(),
        exit_code: 127,
        output: "bash: apt: command not found".into(),
        timestamp: 0,
        ai_origin: false,
    });
}
#[test]
fn screenshot_cases_get_concrete_native_update_advice() {
    let arch = Host::from_os_release("ID=cachyos\nID_LIKE=arch");
    for command in ["apt update", "apt upgrade", "apt get upgrade"] {
        let mut req = request("continue", "");
        failed(&mut req, command);
        for text in ["continue", "explain the error", "explain that error"] {
            req.text = text.into();
            let response = guidance::known_response(&req, &arch).unwrap();
            assert_eq!(
                response
                    .command
                    .as_deref()
                    .unwrap()
                    .trim_start_matches("sudo "),
                "pacman -Syu"
            );
            assert!(response.explanation.unwrap().contains("Arch-based"));
            assert!(response.question.is_none());
        }
        let typed = request(command, command);
        assert!(guidance::known_response(&typed, &arch)
            .unwrap()
            .command
            .is_some());
    }
}
#[test]
fn host_guidance_does_not_use_old_errors_for_new_tasks_or_remote_hosts() {
    let arch = Host::from_os_release("ID=cachyos\nID_LIKE=arch");
    let mut req = request("show disk space", "");
    failed(&mut req, "apt update");
    assert!(guidance::known_response(&req, &arch).is_none());
    req.text = "continue".into();
    req.session.remote = true;
    assert!(guidance::known_response(&req, &arch).is_none());
    req.session.remote = false;
    let debian = Host::from_os_release("ID=debian");
    assert!(guidance::known_response(&req, &debian).is_none());
}
#[test]
fn bare_find_and_missing_operands_receive_idle_guidance_without_inference() {
    for text in [
        "find",
        "find .",
        "find . -name",
        "find . -size",
        "find . -type",
    ] {
        assert!(host::passive_eligible(text, true, false));
        let answer = worker::process_model_candidate(&request(text, text), |_| {
            panic!("known find input must not invoke Qwen")
        })
        .unwrap();
        assert!(!answer.response.explanation.as_ref().unwrap().is_empty());
        {
            assert!(
                answer.validation.is_none(),
                "must not invent missing argument"
            );
        }
    }
}
#[test]
fn find_glob_correction_preserves_root_and_literal_pattern() {
    let text = "find /tmp -name *.log";
    let answer =
        worker::process_model_candidate(&request(text, text), |_| panic!("no inference needed"))
            .unwrap();
    assert!(answer.validation.is_none());
    assert!(answer.response.command.is_none());
    assert!(answer.response.explanation.unwrap().contains("Quote"));
    let safe = "find /tmp -name '*.log'";
    assert!(
        worker::process_model_candidate(&request(safe, safe), |_| panic!("no inference needed"))
            .unwrap()
            .validation
            .is_none()
    );
}
#[test]
fn unverifiable_prose_requires_explicit_retry() {
    let mut req = request("explain the error", "");
    req.passive = false;
    let mut calls = 0;
    assert!(worker::process_model_candidate(&req, |_| {
        calls += 1;
        Ok(r#"{"action":"clarify","question":"What did you expect?"}"#.into())
    })
    .unwrap_err()
    .to_string()
    .starts_with("Unverifiable:"));
    assert_eq!(calls, 1);
    assert!(guidance::check_response(
        &Response::parse(r#"{"action":"clarify","question":"Which directory should I search?"}"#)
            .unwrap()
    )
    .is_ok());
}

#[test]
fn reading_readme_uses_current_directory_not_old_package_advice() {
    let dir = tempfile::tempdir().unwrap();
    std::fs::write(dir.path().join("README.md"), "# Example").unwrap();
    std::fs::write(dir.path().join("a"), "unrelated").unwrap();
    let mut req = request("read the readme file", "");
    req.passive = false;
    req.session.cwd = dir.path().display().to_string();
    req.session.remember("User: update my system".into());
    req.session.remember("Assistant: pacman -Si READ".into());
    failed(&mut req, "apt upgrade");
    let answer =
        worker::process_model_candidate(&req, |_| panic!("file viewing must not infer")).unwrap();
    let command = answer.validation.unwrap().command;
    let words = host::parse_commands(&command).unwrap();
    assert!(["less", "cat"].contains(&words[0][0].as_str()));
    assert_eq!(words[0][1], "./README.md");
    assert!(answer.response.explanation.unwrap().contains("README.md"));
}

#[test]
fn file_guidance_handles_missing_ambiguous_and_quoted_names() {
    let dir = tempfile::tempdir().unwrap();
    let mut req = request("read the readme file", "");
    req.passive = false;
    req.session.cwd = dir.path().display().to_string();
    let answer = worker::process_model_candidate(&req, |_| panic!("no inference")).unwrap();
    assert!(answer.validation.is_none());
    assert!(answer
        .response
        .explanation
        .unwrap()
        .contains("exact filename"));
    for name in ["README.md", "README.txt"] {
        std::fs::write(dir.path().join(name), "").unwrap();
    }
    req.text = "read README.md.tmp".into();
    let mismatch =
        worker::process_model_candidate(&req, |_| panic!("known file guidance must not infer"))
            .unwrap();
    assert!(
        mismatch.validation.is_none(),
        "filename prefix must not select a different file"
    );
    req.text = "read the readme file".into();
    let answer = worker::process_model_candidate(&req, |_| panic!("no inference")).unwrap();
    assert!(answer.validation.is_none());
    assert!(answer.response.explanation.unwrap().contains("Which file"));
    let name = "notes 'draft'.md";
    std::fs::write(dir.path().join(name), "").unwrap();
    req.text = format!("show the contents of {name}");
    let answer = worker::process_model_candidate(&req, |_| panic!("no inference")).unwrap();
    assert_eq!(
        host::parse_commands(&answer.validation.unwrap().command).unwrap()[0][1],
        format!("./{name}")
    );
}

#[test]
fn editor_question_gives_editor_guidance_not_package_commands() {
    let mut req = request("what is the terminal text file editor", "");
    req.passive = false;
    req.session.remember("Assistant: pacman -Si READ".into());
    let answer =
        worker::process_model_candidate(&req, |_| panic!("editor discovery must not infer"))
            .unwrap();
    assert!(answer.response.explanation.is_some());
    if let Some(v) = answer.validation {
        assert!(["nano", "micro", "nvim", "vim", "vi"].contains(&v.command.as_str()));
    }
    for text in [
        "read the README.md",
        "what is the terminal text file editor",
    ] {
        for command in [
            "pacman -Si READ",
            "sudo pacman -S nano",
            "/usr/bin/apt install nano",
        ] {
            assert!(
                caiman_terminal::command_validation::check_intent(command, text, false).is_err()
            );
        }
    }
    assert!(guidance::file_intent("install a terminal text editor").is_none());
    req.session.remote = true;
    assert!(guidance::known_response(&req, Host::local()).is_none());
}

#[test]
fn a_new_question_overrides_remembered_intent_in_model_validation() {
    let mut req = request("show the contents of README.md", "");
    req.passive = false;
    // Remote requests skip local filesystem guidance, exercising model validation.
    req.session.remote = true;
    req.session.remember("User: update my system".into());
    let mut calls = 0;
    let answer = worker::process_model_candidate(&req, |_| {
        calls += 1;
        Ok(if calls == 1 {
            r#"{"action":"suggest_command","command":"pacman -Si READ","explanation":"Package info"}"#.into()
        } else {
            r#"{"action":"explain","explanation":"Use a text viewer to read the README on the remote host."}"#.into()
        })
    });
    assert!(answer.is_err());
    assert_eq!(calls, 0, "Unknown remote host must not reach inference");
}
