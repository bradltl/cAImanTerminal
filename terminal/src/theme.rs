use anyhow::{bail, Result};
use serde::Deserialize;
use std::{
    path::{Path, PathBuf},
    sync::OnceLock,
};

#[derive(Debug, Deserialize)]
pub struct Theme {
    pub id: String,
    pub name: String,
    pub background: String,
    pub foreground: String,
    pub cursor: String,
    pub surface: String,
    pub selection: String,
    pub accent: String,
    pub muted: String,
    pub palette: [String; 16],
}
impl Theme {
    pub fn css_with_font(&self, size: u32) -> String {
        format!(
            "{}\n.assistant-terminal, .assistant-terminal text {{ font-size: {size}pt; }}",
            self.css()
        )
    }
    pub fn css(&self) -> String {
        let mut css = include_str!("../resources/style.css").to_string();
        for (key, value) in [
            ("background", &self.background),
            ("foreground", &self.foreground),
            ("surface", &self.surface),
            ("selection", &self.selection),
            ("accent", &self.accent),
            ("muted", &self.muted),
        ] {
            css = css.replace(&format!("{{{key}}}"), value);
        }
        css
    }
}
pub fn all() -> &'static [Theme] {
    static THEMES: OnceLock<Vec<Theme>> = OnceLock::new();
    THEMES.get_or_init(|| {
        serde_json::from_str(include_str!("../resources/themes/presets.json"))
            .expect("bundled palettes must be valid")
    })
}
pub fn find(id: &str) -> Option<&'static Theme> {
    all().iter().find(|t| t.id == id)
}
pub fn default_theme() -> &'static Theme {
    &all()[0]
}
pub fn settings_path() -> Result<PathBuf> {
    crate::settings::path()
}
pub fn load(path: &Path) -> Result<&'static Theme> {
    let settings = crate::settings::load(path)?;
    Ok(find(&settings.theme).expect("validated theme"))
}
pub fn save(path: &Path, id: &str) -> Result<()> {
    if find(id).is_none() {
        bail!("Unknown theme: {id}");
    }
    let mut settings = crate::settings::load(path)?;
    settings.theme = id.to_string();
    crate::settings::save(path, &settings)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn palettes_are_complete_and_css_tokens_resolve() {
        assert_eq!(all().len(), 6);
        let color = regex::Regex::new(r"^#[0-9a-fA-F]{6}$").unwrap();
        let mut ids = std::collections::HashSet::new();
        for theme in all() {
            assert!(ids.insert(&theme.id));
            for c in theme.palette.iter().chain([
                &theme.background,
                &theme.foreground,
                &theme.cursor,
                &theme.surface,
                &theme.selection,
                &theme.accent,
                &theme.muted,
            ]) {
                assert!(color.is_match(c));
            }
            assert!(!theme.css().contains("{background}"));
            assert!(theme.css().contains(&theme.background));
        }
    }
    #[test]
    fn preferences_roundtrip_and_preserve_other_settings() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("settings.json");
        assert_eq!(load(&path).unwrap().id, "cayman");
        std::fs::write(&path, r#"{"other":42}"#).unwrap();
        save(&path, "nord").unwrap();
        assert_eq!(load(&path).unwrap().id, "nord");
        let value: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        assert_eq!(value["other"], 42);
        assert!(save(&path, "unknown").is_err());
        std::fs::write(&path, "broken").unwrap();
        assert!(save(&path, "dracula").is_err());
        assert_eq!(std::fs::read_to_string(path).unwrap(), "broken");
    }
}
