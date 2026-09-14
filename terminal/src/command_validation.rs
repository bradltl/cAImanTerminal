//! Host facts and bounded CLI evidence. Candidate commands are parsed, never run.
use crate::command_profiles::help_route;
use crate::host::{executable_exists, parse_commands, probe};
use anyhow::{bail, Result};
use std::{
    collections::HashMap,
    sync::{Mutex, OnceLock},
};

#[derive(Debug, Clone)]
pub struct Host {
    pub os: String,
    pub package_manager: Option<&'static str>,
}
impl Host {
    pub fn from_os_release(release: &str) -> Self {
        let value = |key: &str| {
            release
                .lines()
                .find_map(|l| l.strip_prefix(key))
                .unwrap_or("")
                .trim_matches(['\'', '"'])
                .to_string()
        };
        let id = value("ID=");
        let like = value("ID_LIKE=");
        let family = format!("{id} {like}");
        let has = |names: &[&str]| family.split_whitespace().any(|s| names.contains(&s));
        let package_manager = if has(&["arch", "cachyos", "manjaro", "endeavouros"]) {
            Some("pacman")
        } else if has(&["debian", "ubuntu"]) {
            Some("apt")
        } else if has(&["fedora", "rhel", "centos"]) {
            Some("dnf")
        } else if has(&["suse", "opensuse", "opensuse-tumbleweed"]) {
            Some("zypper")
        } else if has(&["alpine"]) {
            Some("apk")
        } else {
            None
        };
        Self {
            os: format!(
                "{id} (family: {like}); native package manager: {}",
                package_manager.unwrap_or("unknown")
            ),
            package_manager,
        }
    }
    pub fn local() -> &'static Self {
        static HOST: OnceLock<Host> = OnceLock::new();
        HOST.get_or_init(|| crate::platform::local().detect())
    }
    pub fn check_manager(&self, executable: &str) -> Result<()> {
        if let Some(native) = self.package_manager {
            let manager = if executable == "apt-get" {
                "apt"
            } else if executable == "yum" {
                "dnf"
            } else {
                executable
            };
            if ["apt", "dnf", "pacman", "zypper", "apk"].contains(&manager) && manager != native {
                bail!(
                    "'{executable}' is not the native package manager for {}; use {native}",
                    self.os
                );
            }
        }
        Ok(())
    }
}
fn unwrap_sudo(words: &[String]) -> Result<&[String]> {
    if words[0] != "sudo" {
        return Ok(words);
    }
    if words
        .get(1)
        .is_none_or(|w| w.starts_with('-') || w == "sudo")
    {
        bail!("Use a direct sudo command without wrapper options");
    }
    Ok(&words[1..])
}
pub fn check_host(command: &str, remote: bool) -> Result<()> {
    let commands = parse_commands(command)?;
    for words in &commands {
        let sudo = words[0] == "sudo";
        let words = unwrap_sudo(words)?;
        let exe = words[0].as_str();
        if !remote {
            Host::local().check_manager(exe)?;
            if !executable_exists(exe) {
                bail!(
                    "Executable '{exe}' is not available in trusted system paths. {}",
                    Host::local().os
                );
            }
            if sudo && !executable_exists("sudo") {
                bail!("sudo is unavailable on this host");
            }
            if exe == "pacman" {
                let args = &words[1..];
                let short_has = |letter: char| {
                    args.iter()
                        .any(|a| a.starts_with('-') && !a.starts_with("--") && a.contains(letter))
                };
                let has = |flag: &str| args.iter().any(|a| a == flag);
                let help = short_has('h') || short_has('V') || has("--help") || has("--version");
                let operation = "SQRFDUT".chars().any(short_has)
                    || [
                        "--sync",
                        "--query",
                        "--remove",
                        "--files",
                        "--database",
                        "--upgrade",
                        "--deptest",
                    ]
                    .iter()
                    .any(|f| has(f));
                if !operation && !help {
                    bail!("pacman requires an operation such as -Q (query) or -S (sync)");
                }
                let sync = short_has('S') || has("--sync");
                let sync_read = "silgp".chars().any(short_has)
                    || ["--search", "--info", "--list", "--groups", "--print"]
                        .iter()
                        .any(|f| has(f));
                let sync_write = sync
                    && (!sync_read
                        || "yuc".chars().any(short_has)
                        || ["--refresh", "--sysupgrade", "--clean"]
                            .iter()
                            .any(|f| has(f)));
                let mutation = sync_write
                    || "RUD".chars().any(short_has)
                    || ["--remove", "--upgrade", "--database"]
                        .iter()
                        .any(|f| has(f));
                if mutation && !help && !sudo && unsafe { libc::geteuid() } != 0 {
                    bail!("This pacman operation requires administrator privileges; prefix the command with sudo");
                }
            }
            if ["apt", "apt-get"].contains(&exe)
                && words.get(1).is_some_and(|w| !w.starts_with('-'))
            {
                let subcommand = words[1].as_str();
                if ![
                    "update",
                    "upgrade",
                    "full-upgrade",
                    "dist-upgrade",
                    "install",
                    "reinstall",
                    "remove",
                    "purge",
                    "autoremove",
                    "list",
                    "search",
                    "show",
                    "download",
                    "clean",
                    "autoclean",
                    "check",
                    "source",
                    "build-dep",
                    "edit-sources",
                    "help",
                ]
                .contains(&subcommand)
                {
                    bail!("Unknown {exe} subcommand '{subcommand}'");
                }
            }
            // A second lookup for an already absent/wrong-distro tool adds no evidence.
            if ["which", "type", "command"].contains(&exe) {
                for target in words[1..].iter().filter(|w| !w.starts_with('-')) {
                    Host::local().check_manager(target)?;
                    if !executable_exists(target) {
                        bail!("'{target}' is already known to be unavailable; suggest an installed alternative instead of another lookup");
                    }
                }
            }
        }
    }
    Ok(())
}

fn help(words: &[String]) -> String {
    let Some((exe, args)) = help_route(words) else {
        return String::new();
    };
    static CACHE: OnceLock<Mutex<HashMap<String, String>>> = OnceLock::new();
    let key = format!("Source: /usr/bin/{exe} {}", args.join(" "));
    let cache = CACHE.get_or_init(Default::default);
    let cache_key = format!("{key}:{}", crate::platform::evidence_key(exe));
    if let Some(value) = cache.lock().unwrap().get(&cache_key) {
        return value.clone();
    }
    let value = probe(exe, &args)
        .ok()
        .filter(|v| !v.trim().is_empty())
        .map(|v| format!("{key}\n{}", crate::context::redact(&v)))
        .unwrap_or_default();
    let mut cache = cache.lock().unwrap();
    if cache.len() >= 128 {
        cache.clear();
    }
    cache.insert(cache_key, value.clone());
    value
}
pub fn documentation(_request: &str, candidate: Option<&str>, remote: bool) -> String {
    if remote {
        return String::new();
    }
    let mut docs = Vec::new();
    if let Some(command) = candidate {
        if let Ok(commands) = parse_commands(command) {
            for words in commands {
                if let Ok(words) = unwrap_sudo(&words) {
                    docs.push(help(words));
                }
            }
        }
    }
    if let Some(manager) = Host::local().package_manager {
        if candidate.is_some_and(|c| check_host(c, false).is_err()) {
            docs.push(help(&[manager.into()]));
        }
    }
    docs.retain(|d| !d.is_empty());
    docs.dedup();
    docs.join("\n\n")
}

/// Unknown programs are documented through man pages, never by executing their
/// arbitrary --help entry point. The page name is data in a fixed argument list.
pub fn flag_documentation(candidate: &str) -> String {
    let Ok(commands) = parse_commands(candidate) else {
        return String::new();
    };
    let Some(words) = commands.last() else {
        return String::new();
    };
    let Ok(words) = unwrap_sudo(words) else {
        return String::new();
    };
    let direct = help(words);
    if !direct.is_empty() {
        return direct;
    }
    let valid_name = |name: &str| {
        !name.is_empty()
            && name
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    };
    if !valid_name(&words[0]) || !executable_exists(&words[0]) {
        return String::new();
    }
    let mut pages = Vec::new();
    if words
        .get(1)
        .is_some_and(|w| valid_name(w) && !w.starts_with('-'))
    {
        pages.push(format!("{}-{}", words[0], words[1]));
    }
    pages.push(words[0].clone());
    static CACHE: OnceLock<Mutex<HashMap<String, String>>> = OnceLock::new();
    let cache = CACHE.get_or_init(Default::default);
    for page in pages {
        let key = format!("Source: man {page}");
        let cache_key = format!("{key}:{}", crate::platform::evidence_key("man"));
        let cached = cache.lock().unwrap().get(&cache_key).cloned();
        let value = cached.unwrap_or_else(|| {
            let value = probe("man", &["-P", "cat", "--", &page])
                .ok()
                .map(|s| {
                    let mut plain = String::new();
                    for c in s.chars() {
                        if c == '\x08' {
                            plain.pop();
                        } else if !c.is_control() || c == '\n' || c == '\t' {
                            plain.push(c);
                        }
                    }
                    format!("{key}\n{plain}")
                })
                .unwrap_or_default();
            let mut cache = cache.lock().unwrap();
            if cache.len() >= 128 {
                cache.clear();
            }
            cache.insert(cache_key, value.clone());
            value
        });
        if !value.is_empty() {
            return value;
        }
    }
    String::new()
}

/// Options must have local evidence. Unknown coverage fails closed, including
/// nested CLIs whose help route has not been audited. Positional argument
/// semantics (paths, resource IDs, etc.) remain for the user to review.
pub fn check_candidate(command: &str, remote: bool, documentation: &str) -> Result<()> {
    check_host(command, remote)?;
    if remote {
        return Ok(());
    }
    for words in parse_commands(command)? {
        let words = unwrap_sudo(&words)?;
        let exe = words[0].as_str();
        if exe == "command" || exe == "type" {
            continue;
        }
        let needs_help = words[1..].iter().any(|w| w.starts_with('-') && w != "-")
            || ["gh", "gcloud"].contains(&exe);
        if !needs_help {
            continue;
        }
        let Some((_, route)) = help_route(words) else {
            bail!("No audited local help route for '{exe}'; options/subcommands are unverified");
        };
        let header = format!("Source: /usr/bin/{exe} {}\n", route.join(" "));
        let Some((_, rest)) = documentation.split_once(&header) else {
            bail!("Installed help is needed to verify {exe} options");
        };
        let body = rest.split("\n\nSource:").next().unwrap_or(rest);
        let tokens: Vec<_> = body
            .split(|c: char| !(c.is_ascii_alphanumeric() || c == '-' || c == '_'))
            .collect();
        let mut options = true;
        for arg in &words[1..] {
            if arg == "--" {
                options = false;
                continue;
            }
            if !options || !arg.starts_with('-') || arg == "-" {
                continue;
            }
            let flag = arg.split('=').next().unwrap();
            if tokens.contains(&flag) {
                continue;
            }
            if !flag.starts_with("--")
                && flag[1..]
                    .chars()
                    .all(|c| c.is_ascii_alphabetic() && tokens.contains(&format!("-{c}").as_str()))
            {
                continue;
            }
            bail!("Flag '{flag}' was not found in installed {exe} help");
        }
    }
    Ok(())
}

/// A small operation-level contract for system updates. Package searches and
/// file ownership lookups cannot satisfy an update intent even with valid flags.
/// Other task semantics remain outside this initial validator's coverage.
pub fn is_system_update(intent: &str) -> bool {
    let text = intent.trim().to_ascii_lowercase();
    if [
        "update my system",
        "upgrade my system",
        "update the system",
        "upgrade the system",
        "system update",
        "system upgrade",
    ]
    .iter()
    .any(|p| text.contains(p))
    {
        return true;
    }
    parse_commands(&text).ok().is_some_and(|commands| {
        commands.iter().any(|words| {
            // Classification of an observed command is not authorization. Nested
            // sudo remains forbidden by CLI/risk gates, but should not hide the
            // user's previously attempted package-manager operation.
            let mut words = words.as_slice();
            while words.first().is_some_and(|word| word == "sudo") {
                words = &words[1..];
            }
            words.first().is_some_and(|exe| {
                ["apt", "apt-get", "dnf", "yum", "zypper"].contains(&exe.as_str())
                    && words[1..].iter().any(|w| {
                        ["update", "upgrade", "full-upgrade", "dist-upgrade"].contains(&w.as_str())
                    })
            })
        })
    })
}
pub fn check_intent(command: &str, intent: &str, remote: bool) -> Result<()> {
    if crate::guidance::file_intent(intent).is_some() {
        for words in parse_commands(command)? {
            let words = unwrap_sudo(&words)?;
            let exe = std::path::Path::new(&words[0])
                .file_name()
                .and_then(|s| s.to_str())
                .unwrap_or("");
            if [
                "pacman", "apt", "apt-get", "dnf", "yum", "zypper", "apk", "yay", "paru", "brew",
                "pip", "pip3", "npm",
            ]
            .contains(&exe)
            {
                bail!("The user asked to read a file or identify a text editor, not manage packages. Use an appropriate installed viewer/editor or ask for the missing filename.");
            }
        }
    }
    if remote || Host::local().package_manager != Some("pacman") || !is_system_update(intent) {
        return Ok(());
    }
    for words in parse_commands(command)? {
        let words = unwrap_sudo(&words)?;
        if words[0] != "pacman" {
            continue;
        }
        let args = &words[1..];
        let short_has = |letter: char| {
            args.iter()
                .any(|a| a.starts_with('-') && !a.starts_with("--") && a.contains(letter))
        };
        if "siflg".chars().any(short_has)
            || short_has('F')
            || short_has('Q')
            || [
                "--search", "--info", "--files", "--query", "--list", "--groups",
            ]
            .iter()
            .any(|f| args.iter().any(|a| a == f))
        {
            bail!("A package/file search does not perform the requested system update. For this host, the full system upgrade command is sudo pacman -Syu; do not search for a package named 'update'");
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn words(command: &str) -> Vec<String> {
        shlex::split(command).unwrap()
    }
    #[test]
    fn nested_help_routes_are_literal_and_discard_candidate_arguments() {
        let argv = words("gh run list --repo attacker/repo --json status");
        assert_eq!(
            help_route(&argv),
            Some(("gh", vec!["run", "list", "--help"]))
        );
        assert!(help_route(&words("gh run unreviewed --flag")).is_none());
        assert!(help_route(&words("gcloud config set project arbitrary")).is_none());
        assert!(help_route(&words("/tmp/unknown --help")).is_none());
        let argv = words("pacman -Syu arbitrary-package");
        assert_eq!(help_route(&argv), Some(("pacman", vec!["-S", "--help"])));
        let argv = words("pacman --sync --sysupgrade");
        assert_eq!(help_route(&argv), Some(("pacman", vec!["-S", "--help"])));
    }
    #[test]
    fn option_evidence_checks_short_clusters_and_end_of_options() {
        let docs = "Source: /usr/bin/ls --help\n-a, --all\n-l\n";
        assert!(check_candidate("ls -la", false, docs).is_ok());
        assert!(check_candidate("ls -lz", false, docs).is_err());
        assert!(check_candidate("ls --invented", false, docs).is_err());
        assert!(check_candidate("ls -- --invented", false, docs).is_ok());
        assert!(check_candidate("ls --all", false, "Source: /usr/bin/cat --help\n--all").is_err());
    }
}
