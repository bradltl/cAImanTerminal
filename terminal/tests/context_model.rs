//! Optional end-to-end checks with the shipped local model. No suggested command
//! is executed; recorded terminal output is supplied as a fixture.
#![cfg(feature = "inference")]
use caiman_terminal::{
    context::{CommandRecord, Session},
    host,
    inference::LocalModel,
    worker::{process, Request},
};
use std::sync::{atomic::AtomicU64, Arc};

#[test]
#[ignore = "loads the local GGUF and runs inference on recorded terminal context"]
fn distro_error_followup_with_local_model() {
    let model_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join(caiman_terminal::default_model());
    let model = LocalModel::load(&model_path).unwrap();
    let mut session = Session::new(1, "/tmp".into());
    session.at_prompt = true;
    // Deliberately no explicit @ request: infer the update intent from the
    // failed command history, as in the reported desktop interaction.
    for (command, status, output, ai_origin) in [
        ("apt update", 127, "bash: apt: command not found", false),
        (
            "apt get upgrade",
            127,
            "bash: apt: command not found",
            false,
        ),
        ("which apt", 1, "which: no apt in (/usr/bin:/bin)", true),
    ] {
        session.record(CommandRecord {
            command: command.into(),
            cwd: "/tmp".into(),
            exit_code: status,
            output: output.into(),
            timestamp: 0,
            ai_origin,
        });
        let req = Request {
            session: session.clone(),
            text: host::followup_request(command, status, ai_origin, false).unwrap(),
            ticket: 0,
            cancellation: Arc::new(AtomicU64::new(0)),
            passive: true,
        };
        let mut generations = 0;
        let answer = process(&req, |prompt| {
            generations += 1;
            model.generate(prompt, &req.cancellation, 0)
        })
        .unwrap();
        assert_eq!(
            generations, 0,
            "known host errors must not wait for inference"
        );
        assert!(
            answer.validation.is_some(),
            "known system-update failures require an actionable command"
        );
        println!(
            "{command}: {:?} ({} ms; repaired={})",
            answer.response, answer.elapsed_ms, answer.repaired
        );
        if let Some(validation) = &answer.validation {
            assert!(!validation.command.contains("apt"));
            assert!(
                validation.command.contains("-Syu") || validation.command.contains("--sysupgrade"),
                "irrelevant update recommendation: {}",
                validation.command
            );
            assert_ne!(validation.command, command);
        }
        let explanation = answer.response.explanation.as_deref().unwrap_or("");
        assert!(
            answer.validation.is_some()
                || !explanation.is_empty()
                || answer.response.question.is_some()
        );
        session.remember(format!(
            "Assistant: {}",
            serde_json::to_string(&answer.response).unwrap()
        ));
    }
}
