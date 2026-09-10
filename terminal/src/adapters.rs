//! Registration boundary for compiled providers. Configuration selects only
//! registered implementations; it never authorizes arbitrary plugin execution.
use anyhow::{bail, Result};
use std::{path::Path, sync::atomic::AtomicU64};

pub trait ModelBackend {
    fn generate(&self, prompt: &str, cancellation: &AtomicU64, ticket: u64) -> Result<String>;
}
#[cfg(feature = "inference")]
impl ModelBackend for crate::inference::LocalModel {
    fn generate(&self, prompt: &str, cancellation: &AtomicU64, ticket: u64) -> Result<String> {
        self.generate(prompt, cancellation, ticket)
    }
}
#[cfg(feature = "inference")]
pub fn load_model(
    id: &str,
    path: &Path,
    options: &crate::settings::Inference,
) -> Result<Box<dyn ModelBackend>> {
    match id {
        "llama.cpp" => Ok(Box::new(crate::inference::LocalModel::load_with_options(
            path,
            options.clone(),
        )?)),
        _ => bail!("Unsupported model backend: {id}"),
    }
}

pub trait ShellIntegration {
    fn bootstrap(&self) -> &'static str;
    fn argv(&self, rcfile: &Path) -> Vec<String>;
    fn snapshot_key(&self) -> &'static [u8];
    fn stage_key(&self) -> &'static [u8];
}
pub struct Bash;
impl ShellIntegration for Bash {
    fn bootstrap(&self) -> &'static str {
        crate::shell::BASH_INTEGRATION
    }
    fn argv(&self, rcfile: &Path) -> Vec<String> {
        vec![
            "/bin/bash".into(),
            "--noprofile".into(),
            "--rcfile".into(),
            rcfile.to_string_lossy().into_owned(),
            "-i".into(),
        ]
    }
    fn snapshot_key(&self) -> &'static [u8] {
        b"\x18\x07"
    }
    fn stage_key(&self) -> &'static [u8] {
        b"\x18s"
    }
}
pub fn shell(id: &str) -> Result<&'static dyn ShellIntegration> {
    match id {
        "bash" => Ok(&Bash),
        _ => bail!("Unsupported shell integration: {id}"),
    }
}
pub fn validate_selection(settings: &crate::settings::Settings) -> Result<()> {
    if settings.model_backend != "llama.cpp" {
        bail!("Unsupported model backend: {}", settings.model_backend);
    }
    if settings.platform != "auto" {
        bail!("Only automatic host detection is implemented");
    }
    if settings.terminal_backend != "vte" {
        bail!(
            "Unsupported terminal backend: {}",
            settings.terminal_backend
        );
    }
    shell(&settings.shell)?;
    Ok(())
}

pub struct ProviderDescriptor {
    pub id: &'static str,
    pub name: &'static str,
}
pub const MODEL_BACKENDS: &[ProviderDescriptor] = &[ProviderDescriptor {
    id: "llama.cpp",
    name: "llama.cpp (local GGUF)",
}];
pub const TERMINAL_BACKENDS: &[ProviderDescriptor] = &[ProviderDescriptor {
    id: "vte",
    name: "VTE",
}];
pub const SHELL_INTEGRATIONS: &[ProviderDescriptor] = &[ProviderDescriptor {
    id: "bash",
    name: "Bash",
}];
