//! A deliberately small production contract registry. Unknown requests may be
//! explained but never authorize staging. Operands cannot come from model prose.
use crate::{host, worker::Request};
use anyhow::{bail, Result};

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum IntentContract {
    ExactCommand(String),
    Alternatives(Vec<String>),
    ReadFile(String),
    ExplainOrClarify,
}

/// A filename substring is not an operand: README.md.tmp must not authorize
/// reading README.md. Spaced natural-language names retain boundary checks.
pub fn names_file(query: &str, name: &str) -> bool {
    let words = shlex::split(query).unwrap_or_default();
    if words.iter().any(|word| {
        word.strip_prefix("./")
            .unwrap_or(word)
            .eq_ignore_ascii_case(name)
    }) {
        return true;
    }
    if !name.chars().any(char::is_whitespace) {
        return false;
    }
    let query = query.to_lowercase();
    let name = name.to_lowercase();
    let filename_char = |c: char| c.is_alphanumeric() || matches!(c, '/' | '.' | '_' | '-');
    query.match_indices(&name).any(|(index, _)| {
        !query[..index]
            .chars()
            .next_back()
            .is_some_and(filename_char)
            && !query[index + name.len()..]
                .chars()
                .next()
                .is_some_and(filename_char)
    })
}
pub fn generic_readme(query: &str) -> bool {
    shlex::split(query)
        .is_some_and(|words| words.iter().any(|word| word.eq_ignore_ascii_case("readme")))
}

impl IntentContract {
    pub fn resolve(request: &Request) -> Self {
        Self::resolve_for_host(
            request,
            crate::command_validation::Host::local().package_manager,
            unsafe { libc::geteuid() } == 0,
        )
    }

    pub fn resolve_for_host(request: &Request, manager: Option<&str>, root: bool) -> Self {
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
                if manager == Some("pacman") {
                    if root {
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
                            && (names_file(query, name)
                                || (generic_readme(query)
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
