use caiman_terminal::{
    context::{ContextBinding, Session},
    staging::{stage, StageAttempt},
    terminal_backend::{IntegrationKey, TerminalSurface},
    worker::{self, Request},
};
use std::{
    cell::RefCell,
    sync::{atomic::AtomicU64, Arc},
};

#[derive(Default)]
struct RecordingTerminal(RefCell<Vec<u8>>);
impl TerminalSurface for RecordingTerminal {
    fn context_text(&self) -> String {
        String::new()
    }
    fn send_integration_key(&self, key: IntegrationKey) {
        self.0.borrow_mut().extend(key.bytes());
    }
}

#[test]
fn assistant_modules_have_no_arbitrary_pty_write_capability() {
    let ui = include_str!("../src/ui.rs")
        .split("#[cfg(test)]\nmod tests")
        .next()
        .unwrap();
    for source in [
        ui,
        include_str!("../src/worker.rs"),
        include_str!("../src/staging.rs"),
        include_str!("../src/inference.rs"),
    ] {
        assert!(
            !source.contains(".feed_child("),
            "Arbitrary PTY writes must stay outside assistant paths"
        );
    }
    let adapter = include_str!("../src/terminal_backend.rs");
    assert_eq!(adapter.matches(".feed_child(").count(), 1);
    assert!(adapter.contains("self.feed_child(key.bytes())"));
    for key in [IntegrationKey::Snapshot, IntegrationKey::Stage] {
        assert!(!key
            .bytes()
            .iter()
            .any(|b| [b'\r', b'\n', 0x1b, 0x0f].contains(b)));
    }
}

#[test]
fn production_stage_boundary_records_only_fixed_keys_and_rejects_every_stale_dimension() {
    let dir = tempfile::tempdir().unwrap();
    let mut session = Session::new(1, dir.path().display().to_string());
    session.at_prompt = true;
    session.prompt_generation = 7;
    let request = Request {
        session: session.clone(),
        text: "ls".into(),
        ticket: 0,
        cancellation: Arc::new(AtomicU64::new(0)),
        passive: false,
    };
    let answer = worker::process_model_candidate(&request, |_| {
        Ok(r#"{"action":"suggest_command","command":"ls"}"#.into())
    })
    .unwrap();
    let validation = answer.validation.unwrap();
    let binding = validation.binding().unwrap();
    for change in 0..12 {
        let surface = RecordingTerminal::default();
        let mut current = session.clone();
        match change {
            1 => current.id += 1,
            2 => current.request_id += 1,
            3 => current.revision += 1,
            4 => current.prompt_generation += 1,
            5 => current.cwd.push_str("/other"),
            6 => current.edit("edited".into()),
            7 => current.remote = true,
            8 => current.at_prompt = false,
            _ => (),
        }
        let result = stage(
            &surface,
            dir.path(),
            &current,
            StageAttempt {
                command: &validation.command,
                binding,
                ticket: 0,
                current_ticket: u64::from(change == 9),
                alive: change != 10,
                passive: change == 11,
            },
        );
        assert_eq!(result.is_ok(), change == 0, "transition {change}");
        assert_eq!(
            &*surface.0.borrow(),
            if change == 0 {
                IntegrationKey::Stage.bytes()
            } else {
                &[]
            }
        );
    }
}

#[test]
fn hostile_candidate_bytes_never_reach_terminal_even_with_a_current_snapshot() {
    let dir = tempfile::tempdir().unwrap();
    let mut session = Session::new(1, "/tmp".into());
    session.at_prompt = true;
    let binding = ContextBinding::capture(&session);
    for candidate in [
        "ls\r",
        "ls\n",
        "ls\x1b[200~",
        "ls\x1b[201~\r",
        "ls\x0f",
        "ls\x18\x02",
        "echo $(id)",
        "ls && rm -rf /",
        "cat /etc/shadow",
    ] {
        let surface = RecordingTerminal::default();
        assert!(stage(
            &surface,
            dir.path(),
            &session,
            StageAttempt {
                command: candidate,
                binding: &binding,
                ticket: 0,
                current_ticket: 0,
                alive: true,
                passive: false
            }
        )
        .is_err());
        assert!(surface.0.borrow().is_empty());
    }
}
