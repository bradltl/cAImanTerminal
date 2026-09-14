use caiman_terminal::{
    adapters,
    settings::{self, Settings},
};
#[test]
fn old_theme_settings_migrate_and_unknown_fields_survive() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("settings.json");
    std::fs::write(
        &path,
        r#"{"theme":"nord","future":{"value":42},"inference":{"future_option":true}}"#,
    )
    .unwrap();
    let mut config = settings::load(&path).unwrap();
    assert_eq!(config.version, 1);
    assert_eq!(config.idle_ms, 250);
    assert!(!config.inference.gpu_offload);
    assert_eq!(config.inference.gpu_layers, 32);
    config.font_size = 14;
    settings::save(&path, &config).unwrap();
    let value: serde_json::Value = serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    assert_eq!(value["future"]["value"], 42);
    assert_eq!(value["inference"]["future_option"], true);
    let loaded = settings::load(&path).unwrap();
    assert_eq!(loaded.font_size, 14);
    assert_eq!(loaded.theme, "nord");
}
#[test]
fn gpu_preferences_are_opt_in_bounded_and_preserve_unknown_settings() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("settings.json");
    let mut config = Settings::default();
    config.inference.gpu_offload = true;
    config.inference.gpu_layers = 256;
    config
        .inference
        .extra
        .insert("future_option".into(), true.into());
    settings::save(&path, &config).unwrap();
    let loaded = settings::load(&path).unwrap();
    assert!(loaded.inference.gpu_offload);
    assert_eq!(loaded.inference.gpu_layers, 256);
    assert_eq!(loaded.inference.extra["future_option"], true);
    let before = std::fs::read(&path).unwrap();
    for layers in [0, 257, u32::MAX] {
        config.inference.gpu_layers = layers;
        assert!(settings::save(&path, &config).is_err());
        assert_eq!(std::fs::read(&path).unwrap(), before);
    }
    for layers in [1, 32, 256] {
        config.inference.gpu_layers = layers;
        config.validate().unwrap();
    }
    let runtime = settings::InferenceRuntime {
        backend: settings::AccelerationBackend::Vulkan,
        status: settings::AccelerationStatus::OffloadRequested,
        requested_gpu_layers: 32,
    };
    let encoded = serde_json::to_string(&runtime).unwrap();
    assert_eq!(
        serde_json::from_str::<settings::InferenceRuntime>(&encoded).unwrap(),
        runtime
    );
    assert!(runtime.description().contains("requested"));
    assert!(runtime.description().contains("unmeasured"));
}
#[test]
fn invalid_settings_cannot_replace_working_configuration() {
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("settings.json");
    let mut config = Settings::default();
    settings::save(&path, &config).unwrap();
    let before = std::fs::read(&path).unwrap();
    config.inference.output_tokens = 4096;
    assert!(settings::save(&path, &config).is_err());
    assert_eq!(std::fs::read(&path).unwrap(), before);
    std::fs::write(&path, r#"{"version":999}"#).unwrap();
    assert!(settings::load(&path)
        .unwrap_err()
        .to_string()
        .contains("version"));
}
#[test]
fn unsupported_adapters_fail_explicitly_and_model_preference_wins() {
    let mut config = Settings {
        terminal_backend: "future-renderer".into(),
        ..Settings::default()
    };
    assert!(adapters::validate_selection(&config).is_err());
    config.terminal_backend = "vte".into();
    config.shell = "fish".into();
    assert!(adapters::validate_selection(&config).is_err());
    config.shell = "bash".into();
    config.platform = "windows".into();
    assert!(adapters::validate_selection(&config).is_err());
    config.platform = "auto".into();
    config.model_backend = "future-backend".into();
    assert!(adapters::validate_selection(&config).is_err());
    config.model_backend = "llama.cpp".into();
    config.model_path = Some("/tmp/preferred.gguf".into());
    assert_eq!(
        config.resolved_model(),
        std::path::PathBuf::from("/tmp/preferred.gguf")
    );
    // A missing saved model must not prevent the plain terminal from starting.
    config.validate().unwrap();
    assert!(caiman_terminal::default_model().contains("sft-v2.gguf"));
}
