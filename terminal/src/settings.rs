//! Versioned preferences. Unknown fields survive edits for forward compatibility.
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    io::Write,
    path::{Path, PathBuf},
};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub version: u32,
    pub theme: String,
    pub model_path: Option<PathBuf>,
    pub model_backend: String,
    pub platform: String,
    pub terminal_backend: String,
    pub shell: String,
    pub ai_enabled: bool,
    pub show_ai: bool,
    pub idle_ms: u64,
    pub font_size: u32,
    pub scrollback: u32,
    pub inference: Inference,
    #[serde(flatten)]
    pub extra: BTreeMap<String, serde_json::Value>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
pub struct Inference {
    pub model_sha256: Option<String>,
    pub threads: i32,
    pub context_tokens: u32,
    pub output_tokens: usize,
    pub timeout_seconds: u64,
    #[serde(flatten)]
    pub extra: BTreeMap<String, serde_json::Value>,
}
impl Default for Inference {
    fn default() -> Self {
        Self {
            model_sha256: None,
            threads: 2,
            context_tokens: 4096,
            output_tokens: 256,
            timeout_seconds: 45,
            extra: BTreeMap::new(),
        }
    }
}
impl Default for Settings {
    fn default() -> Self {
        Self {
            version: 1,
            theme: "cayman".into(),
            model_path: None,
            model_backend: "llama.cpp".into(),
            platform: "auto".into(),
            terminal_backend: "vte".into(),
            shell: "bash".into(),
            ai_enabled: true,
            show_ai: true,
            idle_ms: 250,
            font_size: 11,
            scrollback: 10000,
            inference: Inference::default(),
            extra: BTreeMap::new(),
        }
    }
}
impl Settings {
    pub fn validate(&self) -> Result<()> {
        if self.version != 1 {
            bail!(
                "Unsupported settings version {}; this app supports version 1",
                self.version
            );
        }
        if crate::theme::find(&self.theme).is_none() {
            bail!("Unknown theme: {}", self.theme);
        }
        crate::adapters::validate_selection(self)?;
        if !(150..=5000).contains(&self.idle_ms) {
            bail!("Assistance delay must be 150–5000 ms");
        }
        if !(8..=32).contains(&self.font_size) {
            bail!("Font size must be 8–32 pt");
        }
        if !(100..=100000).contains(&self.scrollback) {
            bail!("Scrollback must be 100–100000 lines");
        }
        self.inference.validate()?;
        if let Some(path) = &self.model_path {
            if !path.is_absolute() {
                bail!("Model must be an absolute path to an existing local GGUF file");
            }
            if path.extension().and_then(|e| e.to_str()) != Some("gguf") {
                bail!("The llama.cpp backend requires a .gguf model");
            }
        }
        Ok(())
    }
    pub fn resolved_model(&self) -> PathBuf {
        self.model_path
            .clone()
            .or_else(|| std::env::var_os("CAYMAN_DEFAULT_MODEL").map(PathBuf::from))
            .unwrap_or_else(|| crate::default_model().into())
    }
}
impl Inference {
    pub fn validate(&self) -> Result<()> {
        if self
            .model_sha256
            .as_ref()
            .is_some_and(|s| s.len() != 64 || !s.bytes().all(|b| b.is_ascii_hexdigit()))
        {
            bail!("Model SHA-256 must be 64 hexadecimal digits");
        }
        if !(1..=64).contains(&self.threads) {
            bail!("Inference threads must be 1–64");
        }
        if !(2048..=32768).contains(&self.context_tokens) {
            bail!("Context size must be 2048–32768 tokens");
        }
        if !(64..=2048).contains(&self.output_tokens)
            || self.output_tokens + 256 >= self.context_tokens as usize
        {
            bail!("Output budget must be 64–2048 tokens and leave space for input");
        }
        if !(5..=300).contains(&self.timeout_seconds) {
            bail!("Inference timeout must be 5–300 seconds");
        }
        Ok(())
    }
}
pub fn path() -> Result<PathBuf> {
    let base = std::env::var_os("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .filter(|path| path.is_absolute())
        .or_else(|| std::env::var_os("HOME").map(|path| PathBuf::from(path).join(".config")))
        .context("Neither XDG_CONFIG_HOME nor HOME is available")?;
    Ok(base.join("cayman-terminal/settings.json"))
}
pub fn load(path: &Path) -> Result<Settings> {
    if !path.exists() {
        return Ok(Settings::default());
    }
    let settings: Settings = serde_json::from_slice(&std::fs::read(path)?)?;
    settings.validate()?;
    Ok(settings)
}
pub fn save(path: &Path, settings: &Settings) -> Result<()> {
    settings.validate()?;
    // Merge with the latest file so theme quick-actions and future fields survive.
    let mut existing = if path.exists() {
        serde_json::from_slice::<serde_json::Value>(&std::fs::read(path)?)?
    } else {
        serde_json::json!({})
    };
    if existing
        .get("version")
        .and_then(|v| v.as_u64())
        .is_some_and(|v| v != 1)
    {
        bail!("Cannot overwrite a settings file from a newer version");
    }
    let object = existing
        .as_object_mut()
        .context("Settings must be an object")?;
    for (key, value) in serde_json::to_value(settings)?.as_object().unwrap() {
        if key == "inference" {
            let nested = object.entry(key).or_insert_with(|| serde_json::json!({}));
            if let Some(nested) = nested.as_object_mut() {
                nested.extend(value.as_object().unwrap().clone());
            } else {
                *nested = value.clone();
            }
        } else {
            object.insert(key.clone(), value.clone());
        }
    }
    let parent = path.parent().context("Settings path needs a directory")?;
    std::fs::create_dir_all(parent)?;
    let mut temp = tempfile::NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(&mut temp, &existing)?;
    temp.write_all(b"\n")?;
    temp.as_file().sync_all()?;
    temp.persist(path)?;
    Ok(())
}
