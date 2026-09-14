use caiman_terminal::{command_validation, host};

#[test]
fn bounded_tails_preserve_unicode_and_redact_before_cutting_labels() {
    use caiman_terminal::context::{bounded, CommandRecord, Session};
    for size in 0..20 {
        let text = "aé🦀z";
        let expected: String = text
            .chars()
            .skip(text.chars().count().saturating_sub(size))
            .collect();
        assert_eq!(bounded(text, size), expected);
    }
    let mut session = Session::new(1, "/tmp".into());
    for secret in [
        format!("password={}", "x".repeat(100_000)),
        format!("-----BEGIN PRIVATE KEY-----\n{}", "a".repeat(100_000)),
    ] {
        session.record(CommandRecord {
            command: "synthetic".into(),
            cwd: "/tmp".into(),
            exit_code: 0,
            output: secret,
            timestamp: 0,
            ai_origin: false,
        });
        let output = &session.journal.back().unwrap().output;
        assert!(output.contains("redacted") || output.contains("withheld"));
        assert!(!output.contains("xxxxxxxx"));
        assert!(!output.contains("aaaaaaaa"));
    }
}

#[test]
fn nested_sudo_never_hides_risk_but_observed_update_intent_is_retained() {
    for command in [
        "sudo sudo rm -rf /",
        "sudo sudo ls",
        "sudo sudo sudo sh -c id",
    ] {
        assert!(host::assess_risk(command, false, "").is_err(), "{command}");
        assert!(
            command_validation::check_host(command, false).is_err(),
            "{command}"
        );
    }
    assert!(command_validation::is_system_update("sudo sudo apt update"));
    assert!(!command_validation::is_system_update("sudo sudo"));
    assert!(host::assess_risk("sudo ls", false, "").is_ok());
}

#[test]
fn kill_signals_are_distinct_from_pid_and_group_operands() {
    for command in [
        "kill -1 12345",
        "kill -s HUP 12345",
        "kill -n 1 12345",
        "kill -- 12345",
    ] {
        assert!(host::assess_risk(command, false, "").is_ok(), "{command}");
    }
    for command in [
        "kill -1",
        "kill -- -1",
        "kill -9 -12345",
        "kill -s HUP 1",
        "kill 0",
        "kill -n 9 -- -123",
        "kill -9 nonsense",
    ] {
        assert!(host::assess_risk(command, false, "").is_err(), "{command}");
    }
}
