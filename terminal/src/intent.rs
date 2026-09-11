//! A deliberately small production contract registry. Unknown requests may be
//! explained but never authorize staging. Operands cannot come from model prose.
use crate::{host, worker::Request};
use anyhow::{bail, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IntentContract {
    ExactCommand(String),
    Alternatives(Vec<String>),
    ReadFile(String),
    ExplainOrClarify,
}

impl IntentContract {
    pub fn resolve(request: &Request) -> Self {
        if request.passive || request.session.remote {
            return Self::ExplainOrClarify;
        }
        let text = request.text.trim().trim_start_matches('@').trim();
        let lower = text.to_lowercase();
        // Negation and explanatory questions are not execution authorization.
        if lower.contains('?')
            || [
                " don't ",
                " do not ",
                " not ",
                " never ",
                " explain ",
                " what ",
                " why ",
                " how ",
                " dangerous ",
                " without ",
                " continue ",
            ]
            .iter()
            .any(|s| format!(" {lower} ").contains(s))
        {
            return Self::ExplainOrClarify;
        }
        let choices: &[&str] = match lower.as_str() {
            "show disk usage" | "show me disk usage" | "disk usage" => &["df -h", "df -hT"],
            "show memory usage" | "memory usage" => &["free -h"],
            "list files" | "show files" | "list the files" => &["ls", "ls -la"],
            "list files recursively" => &["ls -R", "ls --recursive"],
            "show current directory" | "print working directory" => &["pwd"],
            "show git status" => &["git status"],
            "update my system" | "upgrade my system" => {
                if crate::command_validation::Host::local().package_manager == Some("pacman") {
                    if unsafe { libc::geteuid() } == 0 {
                        &["pacman -Syu"]
                    } else {
                        &["sudo pacman -Syu"]
                    }
                } else {
                    &[]
                }
            }
            _ => &[],
        };
        if !choices.is_empty() {
            return Self::Alternatives(choices.iter().map(|s| (*s).into()).collect());
        }
        if crate::guidance::file_intent(text) == Some(crate::guidance::FileIntent::Read) {
            return Self::ReadFile(lower);
        }
        // An exact literal authorizes only itself. Executable availability is a
        // separate CLI gate, so intent identity is independent of installed tools.
        if host::parse_commands(text).is_ok() {
            return Self::ExactCommand(text.into());
        }
        Self::ExplainOrClarify
    }

    pub fn check(&self, candidate: &str) -> Result<()> {
        let accepted = match self {
            Self::ExactCommand(command) => candidate == command,
            Self::Alternatives(commands) => commands.iter().any(|c| c == candidate),
            Self::ReadFile(query) => host::parse_commands(candidate).is_ok_and(|commands| {
                commands.len() == 1
                    && commands[0].len() == 2
                    && ["cat", "less"].contains(&commands[0][0].as_str())
                    && commands[0][1].strip_prefix("./").is_some_and(|name| {
                        !name.contains('/')
                            && !name.is_empty()
                            && (query.contains(&name.to_lowercase())
                                || (query.contains("readme")
                                    && name.eq_ignore_ascii_case("README.md")))
                    })
            }),
            Self::ExplainOrClarify => false,
        };
        if !accepted {
            bail!("No supported explicit intent authorizes this command; specify the exact command or a supported task");
        }
        Ok(())
    }
}
