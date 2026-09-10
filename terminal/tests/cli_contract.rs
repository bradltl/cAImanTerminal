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
