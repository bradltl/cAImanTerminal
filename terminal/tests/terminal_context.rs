use caiman_terminal::{
    context::{CommandRecord, Session},
    worker::{build_prompt, Request},
};
use std::sync::{atomic::AtomicU64, Arc};

#[test]
fn prompt_combines_live_terminal_input_results_and_conversation() {
    let mut session = Session::new(1, "/workspace/project".into());
    session.at_prompt = true;
    session.edit("cat README.md".into());
    session.remember("Assistant: Previous suggestion only".into());
    session.record(CommandRecord {
        command: "cat missing.md".into(),
        cwd: "/workspace/previous".into(),
        exit_code: 1,
        output: "cat: missing.md: No such file or directory".into(),
        timestamp: 0,
        ai_origin: false,
    });
    session.capture_terminal("README.md\nBUILD.md\napi_key=hidden-value\n", None);
    let request = Request {
        session,
        text: "what does this mean?".into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: false,
    };
    let prompt = build_prompt(&request, "");
    for expected in [
        "CWD: /workspace/project",
        "CWD: /workspace/previous",
        "Current input: cat README.md",
        "README.md\\nBUILD.md",
        "Exit code: 1",
        "Last command failed",
        "No such file or directory",
        "Previous suggestion only",
        "what does this mean?",
    ] {
        assert!(prompt.contains(expected), "missing {expected}: {prompt}");
    }
    assert!(!prompt.contains("hidden-value"));
}

#[test]
fn terminal_snapshots_are_bounded_redacted_and_tab_local() {
    let mut one = Session::new(1, "/one".into());
    let two = Session::new(2, "/two".into());
    one.capture_terminal(
        &format!(
            "{}\nlatest output\npassword=secretvalue\n{}",
            "x".repeat(6000),
            "\n".repeat(4000)
        ),
        Some("cat README.md"),
    );
    assert!(one.terminal_text.chars().count() <= 3000);
    assert!(one.terminal_text.contains("latest output"));
    assert!(!one.terminal_text.contains("secretvalue"));
    assert_eq!(one.running_command.as_deref(), Some("cat README.md"));
    assert!(two.terminal_text.is_empty());
    assert!(two.running_command.is_none());
    one.capture_terminal("new screen", None);
    assert_eq!(one.terminal_text, "new screen");
    assert!(one.running_command.is_none());
}
