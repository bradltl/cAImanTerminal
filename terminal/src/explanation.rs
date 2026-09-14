//! Deterministic descriptions are explicitly host-authored, never model claims.
//! Model suggestions supply their own request-grounded explanation instead.
pub fn command_summary(command: &str) -> String {
    let Ok(commands) = crate::host::parse_commands(command) else {
        return "The host cannot explain this command's syntax reliably.".into();
    };
    let descriptions: Vec<_> = commands
        .iter()
        .map(|words| {
            let words = if words[0] == "sudo" { &words[1..] } else { words.as_slice() };
            match words.first().map(String::as_str) {
                Some("df") => "Reports filesystem disk space; -h uses human-readable sizes and -T includes filesystem types.",
                Some("free") => "Reports memory and swap usage; -h uses human-readable sizes.",
                Some("ls") => "Lists directory entries; -a includes hidden names, -l shows details and -R descends into subdirectories.",
                Some("pwd") => "Prints the current working directory.",
                Some("cat") => "Prints the named file contents to the terminal.",
                Some("less") => "Opens the named file in a pager; press q to leave it.",
                Some("echo") => "Prints the supplied literal arguments to the terminal.",
                Some("mkdir") => "Creates the named directories; -p also creates missing parent directories. Existing files are not replaced.",
                Some("rmdir") => "Removes the named empty directories. It refuses directories that still contain entries.",
                Some("rm") => "Deletes the named entries; -r/-R descends recursively and -f suppresses prompts. No reliable undo is provided; review every target before pressing Enter.",
                Some("cp") => "Copies the source to the destination and may overwrite existing content; -i asks before overwriting and -n avoids overwriting. Review both paths.",
                Some("mv") => "Moves or renames the source to the destination and may overwrite existing content; -i asks before overwriting and -n avoids overwriting. Review both paths.",
                Some("git") if words.get(1).is_some_and(|s| s == "status") => "Reports working-tree and staging-area changes without committing them.",
                Some("pacman") if words.get(1).is_some_and(|s| s == "-Syu") => "Refreshes package databases and upgrades the full Arch system; this changes installed packages and may require administrator privileges.",
                _ => "Preserves the exact command you supplied. The host has not established a complete explanation of its effects; review its documentation and arguments.",
            }
        })
        .collect();
    format!(
        "Host explanation: {}{}",
        descriptions.join(" "),
        if commands.len() > 1 {
            " The pipeline passes each command's output to the next."
        } else {
            ""
        }
    )
}

#[cfg(test)]
mod tests {
    #[test]
    fn host_summaries_describe_effects_without_claiming_model_reasoning_or_execution() {
        for (command, expected) in [
            ("df -h", "disk space"),
            ("sudo pacman -Syu", "changes installed packages"),
            ("git status", "without committing"),
        ] {
            let summary = super::command_summary(command);
            assert!(summary.starts_with("Host explanation:"));
            assert!(summary.contains(expected));
        }
        assert!(super::command_summary("custom-tool")
            .contains("not established a complete explanation"));
    }
}
