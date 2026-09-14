use caiman_terminal::{
    context::{CommandRecord, Session},
    prompt::Prompt,
    worker::{self, Request},
};
use std::sync::{atomic::AtomicU64, Arc};

#[test]
fn every_evidence_source_is_quoted_and_cannot_create_template_roles() {
    let attacks: Vec<String> = serde_json::from_str(include_str!("prompt-injection.json")).unwrap();
    for attack in attacks {
        let mut session = Session::new(1, format!("/tmp/{attack}"));
        session.at_prompt = true;
        session.terminal_text = attack.clone();
        session.input = attack.clone();
        session
            .conversation
            .push_back(format!("Assistant: {attack}"));
        session.record(CommandRecord {
            command: "ls".into(),
            cwd: "/tmp".into(),
            exit_code: 1,
            output: attack.clone(),
            timestamp: 0,
            ai_origin: false,
        });
        let req = Request {
            session,
            text: "show disk usage".into(),
            ticket: 0,
            cancellation: Arc::new(AtomicU64::new(0)),
            passive: false,
        };
        let mut prompt: Prompt =
            serde_json::from_str(&worker::build_prompt(&req, &attack)).unwrap();
        assert!(!prompt.system.contains(&attack));
        let provenance = prompt.provenance.clone();
        // Correction messages can quote rejected model text, so test them too.
        prompt.correction = Some(attack.clone());
        loop {
            let rendered = prompt.render();
            assert!(!rendered.contains("<|"));
            assert!(
                !rendered.contains("[INST]"),
                "template delimiter must be escaped"
            );
            assert_eq!(
                rendered
                    .lines()
                    .filter(|l| *l == "[SYSTEM CONTEXT]")
                    .count(),
                1
            );
            assert_eq!(
                rendered
                    .lines()
                    .filter(|l| *l == "[HOST CORRECTION]")
                    .count(),
                1
            );
            assert_eq!(prompt.request, "show disk usage");
            assert_eq!(prompt.provenance, provenance);
            if !prompt.compact() {
                break;
            }
        }
        let result = worker::process_model_candidate(&req, |_| {
            Ok(r#"{"action":"suggest_command","command":"sh -c id"}"#.into())
        });
        assert!(result.is_err());
    }
}
