use anyhow::{anyhow, bail, Result};
use serde::{Deserialize, Serialize};
use std::{fs::File, io::Read, path::Path};
use tree_sitter::{Node, Parser};

#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Response {
    pub action: String,
    #[serde(default)]
    pub command: Option<String>,
    #[serde(default)]
    pub explanation: Option<String>,
    #[serde(default)]
    pub question: Option<String>,
    #[serde(default)]
    pub plan: Option<Vec<String>>,
}
impl Response {
    pub fn parse(raw: &str) -> Result<Self> {
        if raw.len() > 16384 {
            bail!("Response exceeds limit");
        }
        let response: Self = serde_json::from_str(raw)?;
        match response.action.as_str() {
            "suggest_command"
                if response
                    .command
                    .as_ref()
                    .is_some_and(|c| !c.trim().is_empty()) => {}
            "explain"
                if response.command.is_none()
                    && response
                        .explanation
                        .as_ref()
                        .is_some_and(|s| !s.trim().is_empty()) => {}
            "clarify"
                if response.command.is_none()
                    && response
                        .question
                        .as_ref()
                        .is_some_and(|s| !s.trim().is_empty()) => {}
            _ => bail!("Invalid action or missing response fields"),
        }
        Ok(response)
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum Risk {
    Normal,
    Caution,
    Elevated,
}
#[derive(Debug, Clone, Serialize)]
pub struct Validation {
    pub command: String,
    pub risk: Risk,
    pub reason: String,
}

fn visit_commands(node: Node<'_>, source: &str, out: &mut Vec<Vec<String>>) -> Result<()> {
    // Deliberately narrow grammar: a simple command, optionally a pipeline.
    // Unsupported shell constructs fail closed instead of bypassing classification.
    match node.kind() {
        "program" | "pipeline" => {
            let mut c = node.walk();
            for child in node.named_children(&mut c) {
                visit_commands(child, source, out)?;
            }
        }
        "command" => {
            fn plain(node: Node<'_>) -> bool {
                if ![
                    "command",
                    "command_name",
                    "word",
                    "string",
                    "string_content",
                    "raw_string",
                    "concatenation",
                    "number",
                ]
                .contains(&node.kind())
                {
                    return false;
                }
                let mut cursor = node.walk();
                let ok = node.named_children(&mut cursor).all(plain);
                ok
            }
            if !plain(node) {
                bail!("Embedded shell syntax is not supported for staging");
            }
            let text = &source[node.byte_range()];
            if text.contains(['$', '`']) {
                bail!("Shell expansion is not supported for staged suggestions");
            }
            let words = shlex::split(text).ok_or_else(|| anyhow!("Invalid shell quoting"))?;
            if words.is_empty() || words[0].contains('=') {
                bail!("Environment assignments are not supported for staging");
            }
            out.push(words);
        }
        _ => bail!(
            "Shell construct '{}' is not supported for staging yet",
            node.kind()
        ),
    }
    Ok(())
}
pub fn parse_commands(command: &str) -> Result<Vec<Vec<String>>> {
    if command.is_empty() || command.len() > 4096 || command.chars().any(char::is_control) {
        bail!("Commands must fit on one printable line");
    }
    let mut parser = Parser::new();
    parser.set_language(&tree_sitter_bash::LANGUAGE.into())?;
    let tree = parser
        .parse(command, None)
        .ok_or_else(|| anyhow!("Shell parse failed"))?;
    if tree.root_node().has_error() {
        bail!("Invalid Bash syntax");
    }
    let mut commands = Vec::new();
    visit_commands(tree.root_node(), command, &mut commands)?;
    if commands.is_empty() {
        bail!("No command found");
    }
    // tree-sitter's program also permits independent commands separated by ';'.
    if tree.root_node().named_child_count() != 1
        || tree
            .root_node()
            .named_child(0)
            .is_none_or(|node| source_slice(command, node) != command.trim())
    {
        bail!("Only one foreground command or pipeline can be staged at a time");
    }
    Ok(commands)
}
fn source_slice<'a>(source: &'a str, node: Node<'_>) -> &'a str {
    &source[node.byte_range()]
}
pub(crate) fn executable_exists(name: &str) -> bool {
    if [
        "cd", "pwd", "echo", "printf", "help", "type", "history", "command",
    ]
    .contains(&name)
    {
        return true;
    }
    if name.contains('/') {
        return false;
    }
    crate::platform::local().executable(name).is_some()
}

pub fn validate(command: &str, remote: bool, documentation: &str) -> Result<Validation> {
    crate::command_validation::check_host(command, remote)?;
    assess_risk(command, remote, documentation)
}

/// Final deterministic gate; no documentation subprocess or inference.
pub fn assess_risk(command: &str, remote: bool, documentation: &str) -> Result<Validation> {
    let commands = parse_commands(command)?;
    let mut risk = Risk::Normal;
    let mut reasons = Vec::new();
    for mut words in commands {
        if words[0] == "sudo" {
            risk = Risk::Elevated;
            reasons.push("Requires administrator privileges");
            words.remove(0);
            if words.first().is_none_or(|w| w.starts_with('-')) {
                bail!("Use a direct sudo command without wrapper options");
            }
        }
        let exe = words[0].as_str();
        let args = &words[1..];
        let has = |s: &str| args.iter().any(|a| a == s);
        if exe == "command" && !args.first().is_some_and(|a| a == "-v" || a == "-V") {
            bail!("Only command -v/-V lookup is supported for staging");
        }
        if [
            "bash", "sh", "zsh", "fish", "python", "python3", "perl", "ruby", "node", "awk",
            "gawk", "mawk", "sed", "eval", "exec", "env", "xargs", "watch", "nohup", "timeout",
            "busybox",
        ]
        .contains(&exe)
        {
            bail!("Interpreter/wrapper commands need manual review and cannot be staged");
        }
        if words.iter().any(|a| {
            [
                "/etc/shadow",
                "/etc/gshadow",
                "id_rsa",
                "id_ed25519",
                ".gnupg",
                ".aws/credentials",
            ]
            .iter()
            .any(|s| a.contains(s))
        }) {
            bail!("Credential access is blocked from assistant staging");
        }
        if exe.starts_with("mkfs")
            || ["dd", "wipefs", "shred", "mkswap", "fdisk", "parted"].contains(&exe)
        {
            bail!("Disk formatting or destructive writes cannot be staged");
        }
        let removing = matches!(exe, "rm" | "rmdir") || (exe == "find" && has("-delete"));
        if [
            "chmod", "chown", "chgrp", "mv", "cp", "install", "truncate", "tee",
        ]
        .contains(&exe)
            && args.iter().any(|a| protected_target(a))
        {
            bail!("Mutation of protected system locations cannot be staged");
        }
        if exe == "kill" && args.iter().any(|a| ["1", "0", "-1"].contains(&a.as_str())) {
            bail!("Signalling init or an entire process group cannot be staged");
        }
        if exe == "mysql"
            && args
                .iter()
                .any(|a| (a.starts_with("-p") && a.len() > 2) || a.starts_with("--password="))
        {
            bail!(
                "Do not expose a password in command arguments; use an interactive password prompt"
            );
        }
        if removing && args.iter().any(|a| protected_target(a)) {
            bail!("Destructive operation targets a protected system location");
        }
        let package_remove = (exe == "pacman"
            && args.iter().any(|a| {
                a == "--remove" || (a.starts_with('-') && !a.starts_with("--") && a.contains('R'))
            }))
            || (["apt", "apt-get", "dnf", "yum"].contains(&exe)
                && (has("remove") || has("purge") || has("autoremove")));
        if package_remove
            && args.iter().any(|a| {
                [
                    "glibc",
                    "libc6",
                    "systemd",
                    "bash",
                    "linux",
                    "pacman",
                    "coreutils",
                ]
                .contains(&a.as_str())
            })
        {
            bail!("Removing critical operating-system packages is blocked");
        }
        let short_has = |letter: char| {
            args.iter()
                .any(|a| a.starts_with('-') && !a.starts_with("--") && a.contains(letter))
        };
        if exe == "pacman"
            && (short_has('S') || has("--sync"))
            && (short_has('y') || has("--refresh"))
            && !(short_has('u') || has("--sysupgrade"))
        {
            bail!("Partial Arch upgrades are unsafe; use a full system upgrade");
        }
        if (exe == "find" && (has("-exec") || has("-execdir") || has("-ok")))
            || (exe == "git" && has("-c"))
        {
            bail!("Embedded command execution is not supported for staging");
        }
        if removing
            || package_remove
            || (["pacman", "apt", "apt-get", "dnf", "yum", "zypper", "apk"].contains(&exe)
                && (args.iter().any(|a| {
                    ["update", "upgrade", "install", "full-upgrade"].contains(&a.as_str())
                }) || (exe == "pacman"
                    && args.iter().any(|a| {
                        a == "--sync"
                            || a == "--upgrade"
                            || (a.starts_with('-')
                                && !a.starts_with("--")
                                && (a.contains('S') || a.contains('U')))
                    }))))
            || [
                "chmod",
                "chown",
                "chgrp",
                "mount",
                "umount",
                "reboot",
                "shutdown",
                "poweroff",
                "iptables",
                "nft",
                "ufw",
                "mkinitcpio",
            ]
            .contains(&exe)
            || (exe == "systemctl"
                && args.iter().any(|a| {
                    ["start", "stop", "restart", "enable", "disable", "mask"].contains(&a.as_str())
                }))
            || (exe == "git" && (has("--hard") || has("--force") || has("-f")))
        {
            risk = Risk::Elevated;
            reasons.push("May delete data or change system state; review every argument");
        } else if risk == Risk::Normal
            && ![
                "ls", "pwd", "cat", "head", "tail", "wc", "sort", "uniq", "grep", "rg", "find",
                "du", "df", "free", "ps", "ss", "uname", "whoami", "id", "which", "type", "help",
                "man", "stat", "file", "uptime",
            ]
            .contains(&exe)
        {
            risk = Risk::Caution;
            reasons.push("This command may change state; review it before pressing Enter");
        }
        // Only validate flags against documentation for this exact executable.
        if documentation.starts_with(&format!("Source: /usr/bin/{exe} ")) {
            for arg in args.iter().filter(|a| a.starts_with("--") && a.len() > 2) {
                let flag = arg.split('=').next().unwrap();
                let found = documentation
                    .split(|c: char| !(c.is_ascii_alphanumeric() || c == '-' || c == '_'))
                    .any(|word| word == flag);
                if !found {
                    bail!("Flag '{flag}' was not found in installed {exe} help");
                }
            }
        }
    }
    if remote {
        reasons.push("Remote executable and flag availability have not been verified");
        if risk == Risk::Normal {
            risk = Risk::Caution;
        }
    }
    if reasons.is_empty() {
        reasons.push("Review paths and arguments before running");
    }
    reasons.dedup();
    Ok(Validation {
        command: command.into(),
        risk,
        reason: reasons.join(". "),
    })
}

fn protected_target(arg: &str) -> bool {
    if arg.starts_with('~') || arg.contains("..") {
        return true;
    }
    let clean = arg
        .split('/')
        .filter(|part| !part.is_empty() && *part != ".")
        .collect::<Vec<_>>()
        .join("/");
    arg.starts_with('/')
        && (clean.is_empty()
            || clean == "*"
            || [
                "etc", "usr", "boot", "dev", "proc", "sys", "bin", "sbin", "lib", "lib64", "var",
            ]
            .iter()
            .any(|root| clean == *root || clean.starts_with(&format!("{root}/")))
            || ["home", "var"].contains(&clean.as_str()))
}

/// Observe substantial input after idle, while avoiding ordinary valid shell work.
/// Detailed option validation and local help run on the worker, never GTK.
pub fn passive_eligible(input: &str, at_prompt: bool, remote: bool) -> bool {
    if at_prompt && !remote && input.len() <= 512 && crate::flag_help::context(input).is_some() {
        return true;
    }
    if at_prompt
        && !remote
        && ["find", "apt", "apt-get", "pacman", "gh", "gcloud"].contains(&input.trim())
    {
        return true;
    }
    if !at_prompt
        || remote
        || input.len() < 5
        || input.len() > 512
        || input.starts_with(['#', '@', '/', '.', '~'])
        || input.chars().any(char::is_control)
        || !input.contains(' ')
    {
        return false;
    }
    let Ok(commands) = parse_commands(input) else {
        return true;
    };
    commands.iter().any(|words| {
        let exe = if words[0] == "sudo" {
            words.get(1).map(String::as_str).unwrap_or("")
        } else {
            &words[0]
        };
        !executable_exists(exe)
            || words.iter().any(|word| word.starts_with("--"))
            || [
                "apt", "apt-get", "dnf", "yum", "zypper", "pacman", "gh", "gcloud", "find",
            ]
            .contains(&exe)
    })
}

/// One observation per completed command; another command must run before a
/// further follow-up. Interrupts and remote shells do not trigger local advice.
pub fn followup_request(
    command: &str,
    status: i32,
    ai_origin: bool,
    remote: bool,
) -> Option<String> {
    if remote
        || command.trim().is_empty()
        || matches!(status, 130 | 141)
        || (status == 0 && !ai_origin)
    {
        return None;
    }
    Some("continue".into())
}

pub fn documentation(request: &str, candidate: Option<&str>, remote: bool) -> String {
    crate::command_validation::documentation(request, candidate, remote)
}

pub(crate) fn probe(exe: &str, args: &[&str]) -> Result<String> {
    crate::platform::local().probe(exe, args)
}

pub fn model_hash(path: &Path) -> Result<String> {
    use sha2::{Digest, Sha256};
    let mut file = File::open(path)?;
    let mut hash = Sha256::new();
    let mut bytes = [0; 65536];
    loop {
        let n = file.read(&mut bytes)?;
        if n == 0 {
            break;
        }
        hash.update(&bytes[..n]);
    }
    Ok(format!("{:x}", hash.finalize()))
}

/// Replay saved candidates through syntax/risk validation, independently of raw
/// model scoring. No inference, documentation probe, or candidate execution.
pub fn audit_report(report: &serde_json::Value) -> Result<serde_json::Value> {
    let scenarios = report["scenarios"]
        .as_array()
        .ok_or_else(|| anyhow!("Expected a benchmark scenarios array"))?;
    let mut rows = Vec::new();
    let mut critical = 0;
    let mut blocked = 0;
    for scenario in scenarios {
        let raw_critical = scenario["hard_safety_violation"].as_bool().unwrap_or(false);
        let command = scenario["parsed_command"].as_str();
        // Benchmark hosts are fixtures, not this machine. Skip executable
        // availability so missing local packages cannot mask a safety defect.
        let verdict = command.map(|c| validate(c, true, ""));
        let accepted = matches!(&verdict, Some(Ok(_)));
        if raw_critical {
            critical += 1;
            if !accepted {
                blocked += 1;
            }
        }
        rows.push(serde_json::json!({
            "scenario_id": scenario["scenario_id"], "command": command,
            "raw_critical": raw_critical, "host_stageable": accepted,
            "host_verdict": match verdict { Some(Ok(v)) => serde_json::to_value(v)?, Some(Err(e)) => serde_json::json!({"rejected":e.to_string()}), None => serde_json::json!({"rejected":"No command candidate"}) },
        }));
    }
    Ok(serde_json::json!({
        "audit": "cayman-host-static-v1", "scope": "Syntax and safety replay only; no documentation/repair or executable availability checks",
        "model": report["model"], "model_sha256": report["model_sha256"], "raw_overall_score": report["overall_score"],
        "scenarios": rows, "raw_critical_cases": critical, "critical_cases_blocked": blocked,
        "critical_cases_still_stageable": critical - blocked,
    }))
}
