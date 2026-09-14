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

#[test]
fn policy_check_evaluates_the_supplied_response_instead_of_canonical_shortcuts() {
    use std::{io::Write, process::Stdio};
    for (response, expected) in [
        (r#"{"action":"suggest_command","command":"ls"}"#, false),
        (
            r#"{"action":"suggest_command","command":"pwd","explanation":"Prints the current directory."}"#,
            false,
        ),
        (
            r#"{"action":"suggest_command","command":"ls","explanation":"Lists directory entries."}"#,
            true,
        ),
    ] {
        let mut child = Command::new(env!("CARGO_BIN_EXE_caiman-terminal"))
            .arg("--policy-check")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(
                serde_json::json!({"request":"ls", "response":response})
                    .to_string()
                    .as_bytes(),
            )
            .unwrap();
        let result = child.wait_with_output().unwrap();
        assert!(result.status.success());
        let result: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
        assert_eq!(result["stageable"], expected, "{response}");
        assert_eq!(
            result["inferences"], 1,
            "raw response must enter the worker model branch"
        );
    }
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
