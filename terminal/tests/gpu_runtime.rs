#![cfg(feature = "inference")]

use caiman_terminal::{
    context::Session,
    inference::LocalModel,
    settings::{AccelerationBackend, AccelerationStatus, Inference},
    worker::{self, Request},
};
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Arc,
};

#[test]
fn deterministic_headless_response_does_not_claim_model_or_gpu_loading() {
    let dir = tempfile::tempdir().unwrap();
    let model = dir.path().join("not-loaded.gguf");
    std::fs::write(&model, b"deliberately not a model").unwrap();
    let mut settings = caiman_terminal::settings::Settings::default();
    settings.inference.gpu_offload = true;
    caiman_terminal::settings::save(&dir.path().join("cayman-terminal/settings.json"), &settings)
        .unwrap();
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_caiman-terminal"))
        .env("XDG_CONFIG_HOME", dir.path())
        .args([
            "--model",
            model.to_str().unwrap(),
            "--ask",
            "show disk usage",
        ])
        .output()
        .unwrap();
    assert!(output.status.success());
    let report: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report.get("runtime"), Some(&serde_json::Value::Null));
    assert!(report["validation"].is_object());
}

/// Opt-in local hardware/model smoke, deliberately not a GPU speed claim.
#[test]
#[ignore = "loads the verified local GGUF twice; optional GPU hardware"]
fn verified_model_cpu_and_requested_gpu_preserve_validation_and_cancellation() {
    let path = std::env::var_os("CAIMAN_TEST_MODEL")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| {
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .parent()
                .unwrap()
                .join(caiman_terminal::default_model())
        });
    for gpu_offload in [false, true] {
        let options = Inference {
            gpu_offload,
            ..Default::default()
        };
        let model = LocalModel::load_with_options(&path, options).unwrap();
        let runtime = model.runtime();
        if !gpu_offload {
            assert_eq!(runtime.backend, AccelerationBackend::Cpu);
            assert_eq!(runtime.status, AccelerationStatus::CpuDisabled);
        } else if !cfg!(any(feature = "gpu-vulkan", feature = "gpu-cuda")) {
            assert_eq!(runtime.backend, AccelerationBackend::Cpu);
            assert_eq!(runtime.status, AccelerationStatus::CpuUnavailable);
        }
        // Separate sessions and fresh KV must not change the fixed request's
        // host-validated meaning. Never execute the resulting command.
        for session_id in [81, 82] {
            let mut session = Session::new(session_id, "/tmp".into());
            session.at_prompt = true;
            let request = Request {
                session,
                text: "show disk usage".into(),
                ticket: 0,
                cancellation: Arc::new(AtomicU64::new(0)),
                passive: false,
            };
            let answer = worker::process_model_candidate(&request, |prompt| {
                model.generate(prompt, &request.cancellation, request.ticket)
            })
            .unwrap();
            let validation = answer
                .validation
                .as_ref()
                .expect("correct response must validate");
            assert!(["df -h", "df -hT"].contains(&validation.command.as_str()));
            request.cancellation.store(1, Ordering::Relaxed);
            assert!(model
                .generate("not a prompt", &request.cancellation, 0)
                .unwrap_err()
                .to_string()
                .contains("cancelled"));
        }
        println!(
            "{}",
            serde_json::json!({"runtime": runtime, "validated_sessions": 2, "cancelled_before_decode": true})
        );
    }
}
