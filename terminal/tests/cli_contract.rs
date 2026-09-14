use std::process::Command;

#[test]
fn renamed_executable_exposes_help_and_manual() {
    let output = Command::new(env!("CARGO_BIN_EXE_caiman-terminal"))
        .arg("--help")
        .output()
        .expect("launch caiman-terminal");
    assert!(output.status.success());
    let help = String::from_utf8(output.stdout).unwrap();
    assert!(help.contains("cAIman Terminal"));
    assert!(help.contains("Manual: man caiman-terminal"));
    assert!(!help.contains("man cayman-terminal"));
}

#[cfg(feature = "inference")]
#[test]
fn model_helper_reports_digest_and_native_load_failures_without_crashing_parent() {
    use sha2::{Digest, Sha256};
    let dir = tempfile::tempdir().unwrap();
    let model = dir.path().join("invalid.gguf");
    std::fs::write(&model, b"not a GGUF model").unwrap();
    for digest in [
        "0".repeat(64),
        format!("{:x}", Sha256::digest(b"not a GGUF model")),
    ] {
        let result = Command::new(env!("CARGO_BIN_EXE_caiman-terminal"))
            .env("XDG_CONFIG_HOME", dir.path())
            .args([
                "--model",
                model.to_str().unwrap(),
                "--model-sha256",
                &digest,
                "--ask",
                "explain Unix permissions",
            ])
            .output()
            .unwrap();
        assert!(!result.status.success());
        assert!(
            result.status.code().is_some(),
            "Parent must survive native failure"
        );
        assert!(!result.stderr.is_empty());
        assert!(!String::from_utf8_lossy(&result.stderr).contains("not a GGUF model"));
    }
}
