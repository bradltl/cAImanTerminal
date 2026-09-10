//! Prefix-filtered option help from installed documentation, without inference.
use crate::{
    host,
    worker::{Answer, Request},
};
use std::{sync::OnceLock, time::Instant};

pub fn context(input: &str) -> Option<(Vec<String>, String)> {
    if input.chars().any(char::is_control) {
        return None;
    }
    let commands = host::parse_commands(input).ok()?;
    let mut words = commands.last()?.clone();
    if words.first()?.as_str() == "sudo" {
        words.remove(0);
    }
    if words.len() < 2 {
        return None;
    }
    let flag = words.last()?.clone();
    if !flag.starts_with('-') || words[1..words.len() - 1].iter().any(|w| w == "--") {
        return None;
    }
    Some((words, flag))
}

#[derive(Debug)]
struct Entry {
    flags: Vec<String>,
    text: String,
}
fn entries(docs: &str) -> Vec<Entry> {
    static FLAGS: OnceLock<regex::Regex> = OnceLock::new();
    let re = FLAGS
        .get_or_init(|| regex::Regex::new(r"(?:^|[\s,])(--?[A-Za-z0-9][A-Za-z0-9_-]*)").unwrap());
    let mut entries: Vec<Entry> = Vec::new();
    for line in docs.lines().skip(1) {
        let trimmed = line.trim();
        // Option declarations, including ps's BSD aliases ("f, --forest").
        let declaration = trimmed.starts_with('-')
            || trimmed
                .split_once(',')
                .is_some_and(|(left, _)| left.len() <= 2);
        let flags: Vec<_> = re.captures_iter(trimmed).map(|c| c[1].to_owned()).collect();
        if declaration && !flags.is_empty() {
            entries.push(Entry {
                flags,
                text: trimmed.split_whitespace().collect::<Vec<_>>().join(" "),
            });
        } else if line.starts_with(char::is_whitespace) && !trimmed.is_empty() {
            if let Some(last) = entries.last_mut() {
                if last.text.len() < 220 {
                    last.text.push(' ');
                    last.text.push_str(trimmed);
                }
            }
        }
    }
    entries
}

pub fn describe(exe: &str, prefix: &str, docs: &str) -> String {
    if docs.is_empty() {
        return format!("No installed flag documentation is available for {exe}. I can't verify its options yet.");
    }
    let flag = prefix.split('=').next().unwrap_or(prefix);
    let all = entries(docs);
    let mut selected: Vec<_> = all
        .iter()
        .filter(|e| e.flags.iter().any(|f| f.starts_with(flag)))
        .collect();
    // A completed short-option cluster such as -ef still gets per-flag help.
    if selected.is_empty()
        && !flag.starts_with("--")
        && flag.len() > 2
        && flag[1..].chars().all(|c| c.is_ascii_alphabetic())
    {
        selected = all
            .iter()
            .filter(|e| {
                flag[1..]
                    .chars()
                    .any(|c| e.flags.contains(&format!("-{c}")))
            })
            .collect();
    }
    if selected.is_empty() {
        return format!("No documented option matches {prefix} for {exe}. Type - to see available options, or -- to narrow to long options.");
    }
    let more = selected.len() > 12;
    let lines = selected
        .iter()
        .take(12)
        .map(|e| e.text.chars().take(260).collect::<String>())
        .collect::<Vec<_>>()
        .join("\n\n");
    format!(
        "{exe} options matching {prefix}:\n\n{lines}{}",
        if more {
            "\n\nType more of the flag to narrow this list."
        } else {
            ""
        }
    )
}

pub fn answer(request: &Request) -> Option<Answer> {
    if !request.passive || request.session.remote || request.session.input.is_empty() {
        return None;
    }
    let start = Instant::now();
    let (words, prefix) = context(&request.session.input)?;
    // Keep the dedicated missing-operand and safe-glob guidance for find.
    if words[0] == "find"
        && [
            "-name",
            "-iname",
            "-path",
            "-ipath",
            "-type",
            "-size",
            "-mtime",
            "-maxdepth",
            "-mindepth",
        ]
        .contains(&prefix.as_str())
    {
        return None;
    }
    let candidate = shlex::try_join(words.iter().map(String::as_str)).ok()?;
    let docs = crate::command_validation::flag_documentation(&candidate);
    Some(Answer {
        response: host::Response {
            action: "explain".into(),
            command: None,
            explanation: Some(describe(&words[0], &prefix, &docs)),
            question: None,
            plan: None,
        },
        validation: None,
        source: docs.lines().next().unwrap_or("").into(),
        elapsed_ms: start.elapsed().as_millis(),
        repaired: false,
    })
}
