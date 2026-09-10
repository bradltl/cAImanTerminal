//! Fast, host-owned guidance for facts that do not need model inference.
//! Every offered command still crosses installed CLI and deterministic risk gates.
use crate::{
    command_validation::{self, Host},
    host::{self, Response},
    worker::{Answer, Request},
};
use anyhow::Result;
use std::time::Instant;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum FileIntent {
    Read,
    Editor,
}

pub fn file_intent(text: &str) -> Option<FileIntent> {
    let text = text.to_lowercase();
    let words: Vec<_> = text.split(|c: char| !c.is_alphanumeric()).collect();
    let has = |word| words.contains(&word);
    // Installation/removal is a separate intent, even when an editor is named.
    if ["install", "uninstall", "remove", "upgrade", "package"]
        .iter()
        .any(|w| has(w))
    {
        return None;
    }
    if has("editor") && (has("terminal") || has("text") || has("file")) {
        return Some(FileIntent::Editor);
    }
    if (has("readme")
        || text.contains(".md")
        || text.contains("markdown file")
        || text.contains("text file"))
        && ["read", "see", "view", "show", "contents", "cat", "less"]
            .iter()
            .any(|w| has(w))
    {
        return Some(FileIntent::Read);
    }
    None
}

fn file_guidance(request: &Request, intent: FileIntent) -> Response {
    if intent == FileIntent::Editor {
        for (editor, help) in [
            ("nano", "nano is an installed terminal text editor. Ctrl+O saves; Enter confirms the filename; Ctrl+X exits."),
            ("micro", "micro is an installed terminal text editor. Ctrl+S saves and Ctrl+Q quits."),
            ("nvim", "Neovim is installed. Press i to edit, Esc then :w to save, and :q to quit."),
            ("vim", "Vim is installed. Press i to edit, Esc then :w to save, and :q to quit."),
            ("vi", "vi is installed. Press i to edit, Esc then :w to save, and :q to quit."),
        ] {
            if command_validation::check_host(editor, false).is_ok() {
                return response(Some(editor.into()), help.into());
            }
        }
        return response(None, "Common terminal text editors include nano, micro, and Vim. I could not verify one of these on this host. To only display a file, use cat with its filename.".into());
    }
    let query = request.text.to_lowercase();
    let entries = match std::fs::read_dir(&request.session.cwd) {
        Ok(entries) => entries,
        Err(_) => return response(None, "I could not inspect the current directory. What is the path to the file you want to read?".into()),
    };
    let mut names = Vec::new();
    for entry in entries.take(1024).flatten() {
        if !entry.file_type().is_ok_and(|kind| kind.is_file()) {
            continue;
        }
        let Ok(name) = entry.file_name().into_string() else {
            continue;
        };
        if name.chars().any(char::is_control) {
            continue;
        }
        let lower = name.to_lowercase();
        let named = query.contains(&lower)
            && [".md", ".markdown", ".txt"]
                .iter()
                .any(|suffix| lower.ends_with(suffix));
        let readme = query.contains("readme")
            && ["readme", "readme.md", "readme.txt", "readme.markdown"].contains(&lower.as_str());
        if named || readme {
            names.push(name);
        }
    }
    names.sort();
    if names.len() != 1 {
        return response(
            None,
            if names.is_empty() {
                "I could not identify that file in the current directory. What is its exact filename or path?".into()
            } else {
                format!("Which file would you like to read: {}?", names.join(", "))
            },
        );
    }
    let name = &names[0];
    let viewer = if command_validation::check_host("less", false).is_ok() {
        "less"
    } else {
        "cat"
    };
    let path = format!("./{name}");
    let command = shlex::try_join([viewer, path.as_str()]).expect("filename contains no NUL");
    response(
        Some(command),
        format!(
            "Read {name} from the current directory as plain text. {}",
            if viewer == "less" {
                "Use the arrow keys or Space to scroll, / to search, and q to quit."
            } else {
                "cat prints its contents in the terminal."
            }
        ),
    )
}

fn response(command: Option<String>, text: String) -> Response {
    Response {
        action: if command.is_some() {
            "suggest_command"
        } else {
            "explain"
        }
        .into(),
        command,
        explanation: Some(text),
        question: None,
        plan: None,
    }
}

pub fn known_response(request: &Request, host: &Host) -> Option<Response> {
    if request.session.remote {
        return None;
    }
    if let Some(intent) = file_intent(&request.text) {
        return Some(file_guidance(request, intent));
    }
    let query = request
        .text
        .trim()
        .trim_start_matches('@')
        .trim()
        .to_lowercase();
    let observing = request.session.input.is_empty()
        && (query == "continue"
            || [
                "explain the error",
                "explain that error",
                "explain this error",
                "why did that fail",
                "what went wrong",
            ]
            .contains(&query.as_str()));
    let text = if observing {
        let last = request.session.journal.back()?;
        if last.exit_code == 0 {
            return None;
        }
        last.command.as_str()
    } else {
        request.text.trim()
    };
    let commands = host::parse_commands(text).ok()?;
    if commands.len() != 1 {
        return None;
    }
    let mut words = commands[0].as_slice();
    if words.first()?.as_str() == "sudo" {
        words = words.get(1..)?;
    }
    let exe = words.first()?.as_str();
    let lookup = ["which", "type", "command"].contains(&exe);
    let target = if lookup {
        words.iter().skip(1).find(|w| !w.starts_with('-'))?.as_str()
    } else {
        exe
    };
    if host.check_manager(target).is_err() {
        let native = host.package_manager?;
        let update = command_validation::is_system_update(text)
            || (lookup
                && request
                    .session
                    .journal
                    .iter()
                    .rev()
                    .take(3)
                    .any(|r| command_validation::is_system_update(&r.command)));
        if native == "pacman" && update {
            let command = if unsafe { libc::geteuid() } == 0 {
                "pacman -Syu"
            } else {
                "sudo pacman -Syu"
            };
            return Some(response(Some(command.into()), format!("This host is Arch-based and uses pacman. {target} is not its native package manager. To refresh repositories and upgrade the system, use the command below.")));
        }
        return Some(response(None, format!("This host uses {native}; {target} is not its native package manager. Specify the package or operation you need so I can suggest the {native} command.")));
    }
    if !observing && request.passive && exe == "find" {
        return find_guidance(text, words);
    }
    None
}

fn find_guidance(text: &str, words: &[String]) -> Option<Response> {
    // Restrict automatic completion to simple read-only searches. Never guess
    // missing names, modify an action, or change a user-supplied search root.
    if words.iter().any(|w| {
        ["-exec", "-execdir", "-ok", "-delete", "-fprint", "-fprintf"].contains(&w.as_str())
    }) {
        return None;
    }
    if words.len() <= 2 && words.get(1).is_none_or(|w| !w.starts_with('-')) {
        let path = words.get(1).map(String::as_str).unwrap_or(".");
        let candidate = shlex::try_join(["find", path, "-type", "f"]).ok()?;
        return Some(response(Some(candidate), format!("To list files under {path}, use -type f. To search by filename, add -name '*.log' (or -iname for a case-insensitive match).")));
    }
    let last = words.last()?.as_str();
    let hint = match last {
        "-name" | "-iname" | "-path" | "-ipath" => Some("Add a quoted pattern, for example '*.log'. Quoting keeps the shell from expanding it before find runs."),
        "-type" => Some("Add f for regular files, d for directories, or l for symbolic links."),
        "-size" => Some("Add a size, for example +500M for files larger than 500 MiB or -10k for files smaller than 10 KiB."),
        "-mtime" => Some("Add a number of days: -7 means modified within the last seven days; +7 means more than seven whole days ago."),
        "-maxdepth" | "-mindepth" => Some("Add a directory depth, for example -maxdepth 2 to limit recursion to two levels."),
        _ => None,
    };
    if let Some(hint) = hint {
        return Some(response(None, hint.into()));
    }
    // shlex joins preserve literal argument values and quote glob patterns.
    // Only offer this correction when an unquoted pattern is visibly present.
    for pair in words.windows(2) {
        if ["-name", "-iname", "-path", "-ipath"].contains(&pair[0].as_str())
            && pair[1].contains(['*', '?', '['])
            && text.contains(&format!("{} {}", pair[0], pair[1]))
        {
            return Some(response(Some(shlex::try_join(words.iter().map(String::as_str)).ok()?), "Quote the search pattern so find receives it literally instead of the shell expanding it first.".into()));
        }
    }
    // Unknown predicates go to the model plus local-help validation.
    let known = [
        "-name",
        "-iname",
        "-path",
        "-ipath",
        "-type",
        "-size",
        "-mtime",
        "-mmin",
        "-maxdepth",
        "-mindepth",
        "-print",
        "-print0",
        "-empty",
    ];
    if words
        .iter()
        .skip(1)
        .any(|w| w.starts_with('-') && !known.contains(&w.as_str()) && w.parse::<i64>().is_err())
    {
        return None;
    }
    Some(response(None, "To refine this search: -type f selects files, -type d selects directories, -iname matches names without case sensitivity, and -maxdepth limits recursion. Keep filename patterns quoted.".into()))
}

pub fn answer(request: &Request) -> Option<Result<Answer>> {
    let start = Instant::now();
    let response = known_response(request, Host::local())?;
    Some((|| {
        let validation = if let Some(command) = &response.command {
            let docs = host::documentation(&request.text, Some(command), false);
            command_validation::check_candidate(command, false, &docs)?;
            Some(host::assess_risk(command, false, "")?)
        } else {
            None
        };
        Ok(Answer {
            response,
            validation,
            source: String::new(),
            elapsed_ms: start.elapsed().as_millis(),
            repaired: false,
        })
    })())
}

/// Prose is part of the response contract too. This catches known dismissive
/// patterns, not every possible tone defect; concrete host facts bypass prose
/// generation entirely above.
pub fn check_response(response: &Response) -> Result<()> {
    let text = format!(
        "{} {} {}",
        response.explanation.as_deref().unwrap_or(""),
        response.question.as_deref().unwrap_or(""),
        response
            .plan
            .as_ref()
            .map(|p| p.join(" "))
            .unwrap_or_default()
    )
    .to_lowercase();
    if [
        "what did you expect",
        "what do you expect",
        "you should know",
        "obviously",
        "as i already told you",
        "when i run",
        "i ran ",
        "i executed ",
    ]
    .iter()
    .any(|p| text.contains(p))
    {
        anyhow::bail!("Response must be respectful and actionable, and must not claim the assistant executed a command. Explain the observed result or ask only for a specific missing detail.");
    }
    Ok(())
}
