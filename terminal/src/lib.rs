pub mod alpha_policy;
pub mod context;
pub mod host;
#[cfg(feature = "inference")]
pub mod inference;
pub mod intent;
pub mod model_file;
pub mod model_process;
pub mod policy_fixture;
pub mod prompt;
pub mod secrets;
pub mod shell;
pub mod staging;
#[cfg(feature = "desktop")]
pub mod ui;
pub mod worker;

pub mod command_validation;

pub mod guidance;

pub mod flag_help;

pub mod theme;

/// Shared by the executable, installer, and live model harness.
pub fn default_model() -> &'static str {
    include_str!("../resources/default-model.txt").trim()
}

pub mod adapters;
pub mod platform;
pub mod settings;
#[cfg(feature = "desktop")]
pub mod settings_ui;
pub mod terminal_backend;

mod command_profiles;
