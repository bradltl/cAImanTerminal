//! Audited help routes for the currently supported command families.
//! Extend here when CLI syntax changes; candidates never become help arguments.
pub(crate) fn help_route(words: &[String]) -> Option<(&str, Vec<&str>)> {
    let exe = words.first()?.as_str();
    let mut args = vec!["--help"];
    match exe {
        "ps" => args = vec!["--help", "all"],
        "pacman" => {
            for (letter, option, long) in [
                ('S', "-S", "--sync"),
                ('Q', "-Q", "--query"),
                ('R', "-R", "--remove"),
                ('F', "-F", "--files"),
                ('D', "-D", "--database"),
                ('U', "-U", "--upgrade"),
                ('T', "-T", "--deptest"),
            ] {
                if words.iter().skip(1).any(|a| {
                    a == long || (a.starts_with('-') && !a.starts_with("--") && a.contains(letter))
                }) {
                    args = vec![option, "--help"];
                    break;
                }
            }
        }
        "gh" => {
            let paths = [
                "run list",
                "run view",
                "run watch",
                "run download",
                "run rerun",
                "pr list",
                "pr view",
                "pr checks",
                "pr status",
                "pr create",
                "pr checkout",
                "issue list",
                "issue view",
                "issue create",
                "repo view",
                "repo clone",
                "auth status",
                "workflow list",
                "workflow view",
                "workflow run",
            ];
            let mut matched = false;
            for path in paths {
                let parts: Vec<_> = path.split(' ').collect();
                if words
                    .iter()
                    .skip(1)
                    .map(String::as_str)
                    .take(parts.len())
                    .eq(parts.iter().copied())
                {
                    args = parts;
                    args.push("--help");
                    matched = true;
                    break;
                }
            }
            if !matched && words.len() > 1 && !words[1].starts_with('-') {
                if ["run", "pr", "issue", "repo", "auth", "workflow"].contains(&words[1].as_str())
                    && (words.len() == 2 || words[2].starts_with('-'))
                {
                    args = vec![&words[1], "--help"];
                } else {
                    return None;
                }
            }
        }
        "gcloud" => {
            let paths = [
                "compute instances list",
                "compute instances describe",
                "compute zones list",
                "projects list",
                "config list",
                "auth list",
                "storage buckets list",
            ];
            let path = paths.iter().find(|p| {
                let parts: Vec<_> = p.split(' ').collect();
                words
                    .iter()
                    .skip(1)
                    .map(String::as_str)
                    .take(parts.len())
                    .eq(parts.iter().copied())
            });
            if let Some(path) = path {
                args = path.split(' ').collect();
                args.push("--help");
            } else if words.len() > 1 && !words[1].starts_with('-') {
                return None;
            }
        }
        "ls" | "cat" | "head" | "tail" | "wc" | "sort" | "uniq" | "grep" | "rg" | "find" | "du"
        | "df" | "free" | "ss" | "uname" | "id" | "stat" | "file" | "uptime" | "touch"
        | "mkdir" | "cp" | "mv" | "rm" | "rmdir" | "chmod" | "chown" | "systemctl"
        | "journalctl" | "apt" | "apt-get" | "dnf" | "yum" | "zypper" | "apk" | "man" => {}
        _ => return None,
    }
    Some((exe, args))
}
