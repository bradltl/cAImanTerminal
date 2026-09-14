use caiman_terminal::{
    alpha_policy::{self, HostFacts},
    context::Session,
    host::{self, Risk},
    worker::{self, Request},
};
use std::sync::{atomic::AtomicU64, Arc};

fn request(text: &str) -> Request {
    let mut session = Session::new(1, "/tmp".into());
    session.at_prompt = true;
    Request {
        session,
        text: text.into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: false,
    }
}

#[test]
fn explicit_file_operations_are_reviewable_and_keep_their_effects_visible() {
    for command in [
        "mkdir -p ./build/cache",
        "rm -rf ./build",
        "cp -i ./source ./destination",
        "mv -i ./old ./new",
    ] {
        let req = request(command);
        let answer =
            worker::process(&req, |_| panic!("Exact audited commands need no inference")).unwrap();
        let validation = answer.validation.unwrap();
        assert_eq!(validation.command, command);
        assert_ne!(validation.risk, Risk::Normal);
        assert!(validation.binding().unwrap().matches(&req.session));
        assert!(!answer.response.explanation.unwrap().is_empty());
    }
}

#[test]
fn additive_coverage_cannot_authorize_a_different_target_or_task() {
    let facts = HostFacts::local();
    for (text, candidate) in [
        ("show disk usage", "rm -rf ./build"),
        ("rm -rf ./build", "rm -rf ./source"),
    ] {
        let trace = worker::check_candidate(&request(text), candidate, &facts);
        assert_eq!(trace.policy, alpha_policy::VERSION);
        assert_eq!(trace.initial.cli, "valid");
        assert_eq!(trace.initial.intent, "mismatch");
        assert!(!trace.stageable);
    }
}

#[test]
fn copying_from_a_system_path_is_not_confused_with_writing_it() {
    assert!(host::assess_risk("cp -i /etc/fstab ./fstab.backup", false, "").is_ok());
    for command in [
        "cp -i ./fstab.backup /etc/fstab",
        "cp -t /etc ./fstab",
        "cp --target-directory=/etc ./fstab",
        "mv /etc/fstab ./fstab.backup",
        "cp /etc/shadow ./backup",
    ] {
        assert!(host::assess_risk(command, false, "").is_err(), "{command}");
    }
}

#[test]
fn relative_mutations_bind_to_authenticated_cwd_in_policy_worker_and_stage_writer() {
    let facts = HostFacts::local();
    let stage_dir = tempfile::tempdir().unwrap();
    for (cwd, command) in [
        ("/etc", "sudo rm -f fstab"),
        ("/etc", "sudo cp ./backup fstab"),
        ("/etc", "sudo mv fstab backup"),
        ("/usr/local", "rmdir ./old"),
        ("/tmp/../etc/.", "rm -f ./fstab"),
        ("/", "rm -rf etc"),
        ("/etc", "rm -- '-literal-name'"),
        ("/etc", "cp /tmp/source 'destination file' -i"),
        ("relative-cwd", "rm -f ./build"),
        ("/tmp\n", "mv source destination"),
    ] {
        let mut req = request(command);
        req.session.cwd = cwd.into();
        let trace = worker::check_candidate(&req, command, &facts);
        assert_eq!(trace.initial.safety, "blocked", "{cwd}: {command}");
        assert!(!trace.stageable);
        assert!(worker::process_model_candidate(&req, |_| {
            Ok(serde_json::json!({
                "action":"suggest_command", "command":command,
                "explanation":"Synthetic test candidate, never executed."
            })
            .to_string())
        })
        .is_err());
        assert!(
            caiman_terminal::shell::write_stage_bound(stage_dir.path(), command, "", cwd, 1)
                .is_err(),
            "stage writer must independently reject {cwd}: {command}"
        );
        assert!(!stage_dir.path().join("stage").exists());
    }
}

#[test]
fn cwd_checks_distinguish_path_roles_from_flags_and_literal_data() {
    for (cwd, command) in [
        ("/tmp/project", "rm -rf ./build"),
        ("/tmp/project", "rmdir -p ./build/cache"),
        ("/tmp/project", "mv 'old file' 'new file'"),
        ("/tmp/project", "cp /etc/fstab ./fstab.backup -i"),
        ("/etc", "cp fstab /tmp/fstab.backup -i"),
        ("/etc", "rm -f /tmp/synthetic-build"),
        ("/etc", "echo 'fstab'"),
        ("/tmp/project", "rm -- '-literal-name'"),
    ] {
        assert!(
            host::assess_risk_at(command, cwd, false, "").is_ok(),
            "{cwd}: {command}"
        );
    }
    // A quote is shell syntax, not a license to hide a protected destination.
    assert!(host::assess_risk_at("cp source '/etc/fstab' -i", "/tmp/project", false, "").is_err());
    assert!(host::assess_risk_at("rm -rf ../project", "/tmp/project", false, "").is_err());
    assert!(host::assess_risk_at("cp -t destination source", "/tmp/project", false, "").is_err());
    // Never mutate literal command bytes while checking lexical target paths.
    let stage_dir = tempfile::tempdir().unwrap();
    caiman_terminal::shell::write_stage_bound(
        stage_dir.path(),
        "cp /etc/fstab ./backup -i",
        "",
        "/tmp/project",
        8,
    )
    .unwrap();
    let staged = std::fs::read_to_string(stage_dir.path().join("stage")).unwrap();
    assert_eq!(staged, "8\n/tmp/project\n\ncp /etc/fstab ./backup -i\n");
}

#[test]
fn relative_credential_paths_are_checked_without_treating_literal_data_as_paths() {
    let facts = HostFacts::local();
    let stage_dir = tempfile::tempdir().unwrap();
    for command in [
        "cat shadow",
        "less gshadow",
        "cp shadow /tmp/backup",
        "cat /etc/./shadow",
        "cp /etc/./gshadow /tmp/backup",
    ] {
        let mut req = request(command);
        req.session.cwd = "/etc".into();
        let trace = worker::check_candidate(&req, command, &facts);
        assert_eq!(trace.initial.safety, "blocked", "{command}");
        assert!(!trace.stageable);
        assert!(caiman_terminal::shell::write_stage_bound(
            stage_dir.path(),
            command,
            "",
            "/etc",
            1
        )
        .is_err());
    }
    for (cwd, command) in [
        ("/tmp/project", "cat shadow"),
        ("/tmp/project", "cp shadow backup"),
        ("/etc", "echo shadow"),
        ("/etc", "cp fstab /tmp/backup"),
    ] {
        assert!(
            host::assess_risk_at(command, cwd, false, "").is_ok(),
            "{command}"
        );
    }
}
