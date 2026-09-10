fn main() {
    println!("cargo:rerun-if-changed=resources/icons");
    println!("cargo:rerun-if-changed=resources/resources.gresource.xml");
    if std::env::var_os("CARGO_FEATURE_DESKTOP").is_none() {
        return;
    }
    let output =
        std::path::PathBuf::from(std::env::var_os("OUT_DIR").unwrap()).join("cayman.gresource");
    let status = std::process::Command::new("glib-compile-resources")
        .arg("resources/resources.gresource.xml")
        .arg("--sourcedir=resources")
        .arg("--target")
        .arg(output)
        .status()
        .expect("glib-compile-resources is required for desktop builds");
    assert!(status.success(), "failed to compile cAIman icon resources");
}
