//! Shipping deterministic policy. Fixtures replace host facts, never decisions.
//! Documentation is evidence only: text advertising a flag cannot extend this
//! audited capability set. Unknown CLI coverage is not the same as CLI-valid.
use crate::{host, intent::IntentContract, worker::Request};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, sync::LazyLock};

pub const VERSION: &str = "alpha-v1";
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HostFacts {
    pub package_manager: Option<String>,
    pub root: bool,
    pub installed: Vec<String>,
    #[serde(default)]
    pub documentation: BTreeMap<String, String>,
}
impl HostFacts {
    pub fn local() -> Self {
        let mut names: Vec<_> = POLICY["commands"]
            .as_object()
            .unwrap()
            .keys()
            .cloned()
            .collect();
        names.push("sudo".into());
        Self {
            package_manager: crate::command_validation::Host::local()
                .package_manager
                .map(str::to_owned),
            root: unsafe { libc::geteuid() } == 0,
            installed: names
                .into_iter()
                .filter(|s| host::executable_exists(s))
                .collect(),
            documentation: BTreeMap::new(),
        }
    }
}
static POLICY: LazyLock<serde_json::Value> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../resources/alpha-policy.json")).expect("audited policy")
});

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct CandidateDecision {
    pub parser: String,
    pub cli: String,
    pub intent: String,
    pub safety: String,
    pub secret: String,
    pub risk: String,
}
#[derive(Debug, Clone, Serialize)]
pub struct DecisionTrace {
    pub policy: &'static str,
    pub contract: IntentContract,
    pub context: String,
    pub initial: CandidateDecision,
    pub correction: Option<String>,
    pub final_checks: CandidateDecision,
    pub stageable: bool,
    pub final_command: Option<String>,
}

fn skipped() -> CandidateDecision {
    CandidateDecision {
        parser: "skipped".into(),
        cli: "skipped".into(),
        intent: "skipped".into(),
        safety: "skipped".into(),
        secret: "skipped".into(),
        risk: "unknown".into(),
    }
}

fn cli_status(commands: &[Vec<String>], facts: &HostFacts) -> &'static str {
    for command in commands {
        let mut words = command.as_slice();
        let sudo = words[0] == "sudo";
        if sudo {
            if !facts.installed.iter().any(|s| s == "sudo") {
                return "invalid";
            }
            words = &words[1..];
        }
        let Some(exe) = words.first() else {
            return "invalid";
        };
        let Some(profile) = POLICY["commands"].get(exe) else {
            return "unknown";
        };
        if !facts.installed.contains(exe) {
            return "invalid";
        }
        let args = &words[1..];
        if let Some(exact) = profile.get("exact_args") {
            if exe == "pacman"
                && (facts.package_manager.as_deref() != Some("pacman") || (!sudo && !facts.root))
            {
                return "invalid";
            }
            if serde_json::to_value(args).unwrap() != *exact {
                return "invalid";
            }
            continue;
        }
        let prefix: Vec<String> = serde_json::from_value(
            profile
                .get("prefix")
                .cloned()
                .unwrap_or(serde_json::json!([])),
        )
        .unwrap();
        if !args.starts_with(&prefix) {
            return "invalid";
        }
        let flags: Vec<String> = serde_json::from_value(profile["flags"].clone()).unwrap();
        let mut operands = 0;
        let mut options = true;
        for arg in &args[prefix.len()..] {
            if options && arg == "--" {
                options = false;
                continue;
            }
            if options && arg.starts_with('-') && arg != "-" {
                if !flags.contains(arg)
                    && !(arg.starts_with('-')
                        && !arg.starts_with("--")
                        && arg[1..]
                            .chars()
                            .all(|c| c.is_ascii_alphabetic() && flags.contains(&format!("-{c}"))))
                {
                    return "invalid";
                }
            } else {
                operands += 1;
            }
        }
        if operands < profile["min_operands"].as_u64().unwrap()
            || operands > profile["max_operands"].as_u64().unwrap()
        {
            return "invalid";
        }
    }
    "valid"
}

fn check(command: &str, contract: &IntentContract, facts: &HostFacts) -> CandidateDecision {
    let mut result = skipped();
    result.secret = if crate::secrets::check_command(command).is_ok() {
        "clean"
    } else {
        "blocked"
    }
    .into();
    let Ok(commands) = host::parse_commands(command) else {
        result.parser = "invalid".into();
        result.risk = "blocked".into();
        return result;
    };
    result.parser = "valid".into();
    result.cli = cli_status(&commands, facts).into();
    result.intent = if contract.check(command).is_ok() {
        "satisfied"
    } else {
        "mismatch"
    }
    .into();
    match host::assess_risk(command, false, "") {
        Ok(v) => {
            result.safety = "approved".into();
            result.risk = match v.risk {
                host::Risk::Normal => "normal",
                host::Risk::Caution => "caution",
                host::Risk::Elevated => "elevated",
            }
            .into();
        }
        Err(_) => {
            result.safety = "blocked".into();
            result.risk = "blocked".into();
        }
    }
    result
}

/// Used by the desktop worker and conformance driver. Never executes candidates.
pub fn evaluate(request: &Request, candidate: &str, facts: &HostFacts) -> DecisionTrace {
    let contract =
        IntentContract::resolve_for_host(request, facts.package_manager.as_deref(), facts.root);
    let current = request.session.at_prompt
        && !request.session.remote
        && request
            .cancellation
            .load(std::sync::atomic::Ordering::Relaxed)
            == request.ticket
        && request.text.len() <= 4096
        && request.session.input.len() <= 4096
        && request.session.cwd.len() <= 4096;
    let initial = if current {
        check(candidate, &contract, facts)
    } else {
        skipped()
    };
    let mut final_checks = initial.clone();
    let mut final_command = candidate.to_owned();
    let mut correction = None;
    // Only a finite host-owned task alternative can replace an invalid option.
    // Never repair parser, secret, safety failures, or invent literal operands.
    if initial.parser == "valid"
        && initial.secret == "clean"
        && initial.safety == "approved"
        && initial.cli == "invalid"
    {
        if let IntentContract::Alternatives(choices) = &contract {
            if let Some(choice) = choices.first() {
                let original = host::parse_commands(candidate).unwrap();
                let replacement = host::parse_commands(choice).unwrap();
                if original.len() == 1 && original[0][0] == replacement[0][0] {
                    final_checks = check(choice, &contract, facts);
                    final_command = choice.clone();
                    correction = Some("canonical_task_options".into());
                }
            }
        }
    }
    let stageable = current
        && !request.passive
        && final_checks.parser == "valid"
        && final_checks.cli == "valid"
        && final_checks.intent == "satisfied"
        && final_checks.safety == "approved"
        && final_checks.secret == "clean";
    DecisionTrace {
        policy: VERSION,
        contract,
        context: if current { "current" } else { "rejected" }.into(),
        initial,
        correction,
        final_checks,
        stageable,
        final_command: stageable.then_some(final_command),
    }
}
