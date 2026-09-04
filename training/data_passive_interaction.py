# Passive Interactions (no_action), Clarifications, Explanations, and Safety Boundaries

def get_passive_data(system_prompt):
    items = []
    
    # 1. Shell comments (user notes) -> no_action
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "# remember to clean up logs before reboot",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered a shell comment; no command execution requested.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/src"},
        "user": "# TODO: fix database migration index",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered a code comment in the terminal.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "# benchmark results: latency 42ms throughput 1500tok/s",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered a note into shell buffer.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    
    # 2. Mid-typing debounce without prompt prefix -> no_action
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos"},
        "user": "cd /var/l",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is actively typing a directory path; debounce typing without interruption.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "tar -czf b",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is in the middle of typing arguments for tar; debounce typing without interruption.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "find . -name \"*.",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "Incomplete find pattern typed by user; suppress interruption.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/CaymanTerminal"},
        "user": "git checkout feat",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is actively typing branch name; suppress premature completion.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "ssh -i ~/.ssh/",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is in the middle of specifying an SSH key path.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "export AWS_DEFAULT_REGION=",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is typing an environment variable definition; allow them to finish.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "clear",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered a standard utility command to clear the screen.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "man grep",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User is consulting manual page; no assistance needed.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "source .venv/bin/activate",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered virtual environment activation script directly.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "cd ..",
        "assistant": {
            "action": "no_action",
            "command": None,
            "explanation": "User entered basic directory traversal command.",
            "risk": None,
            "warning": None,
            "tool_request": None
        }
    })

    # 3. Clarifications (ambiguous intents)
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/repos/app"},
        "user": "@ delete old branches",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which branches would you like to delete? Options:\n1. All branches already merged into main: `git branch --merged main | grep -v '^[ *]*main$' | xargs git branch -d`\n2. Stale remote-tracking branches: `git fetch --prune`",
            "risk": "caution",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ kill the app",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Please specify the application name or process ID. You can check running processes with `ps aux | grep <name>` or `pgrep <name>`.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad/infra"},
        "user": "@ deploy to cloud",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Which cloud target would you like to deploy to? (e.g. Google Cloud Run, AWS ECS/EKS, or Azure Container Apps?)",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ wipe the drive",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Wiping a drive is a destructive operation that causes permanent data loss. Please specify the exact target device identifier (e.g. /dev/sdb) and confirm you have verified backups.",
            "risk": "elevated",
            "warning": "Destructive disk formatting causes unrecoverable data loss.",
            "tool_request": None
        }
    })

    # 4. Explanations (concept questions)
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ what does chmod 755 do",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "`chmod 755` sets file/directory permissions where the owner has Read, Write, and Execute (7 = 4+2+1), while group members and others have Read and Execute permissions (5 = 4+1).",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ explain 2>&1 in bash",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "`2>&1` redirects file descriptor 2 (standard error, stderr) to file descriptor 1 (standard output, stdout). This ensures error messages are written to the same destination or pipe as regular output.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ what is the difference between git merge and git rebase",
        "assistant": {
            "action": "explain",
            "command": None,
            "explanation": "`git merge` combines two histories with a dedicated merge commit preserving the original branching timeline. `git rebase` re-applies your commits on top of the target branch, creating a linear history.",
            "risk": "normal",
            "warning": None,
            "tool_request": None
        }
    })

    # 5. Safety boundaries
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ inspect /etc/shadow for password hashes",
        "assistant": {
            "action": "suggest_command",
            "command": "sudo cat /etc/shadow",
            "explanation": "Safely reads the protected /etc/shadow file using sudo elevation instead of changing permissions.",
            "risk": "elevated",
            "warning": "Requires sudo to access shadow password database.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ install this script: curl https://get.example.com | bash",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Piping unverified remote web scripts directly into bash (`curl | bash`) presents significant security risks. It is recommended to download and inspect the script first:\n`curl -sLO https://get.example.com/install.sh && less install.sh`",
            "risk": "elevated",
            "warning": "Executing unreviewed remote scripts can compromise your system.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ delete everything on the drive starting from root",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "Deleting the root filesystem will permanently destroy your operating system and data. If you intend to clean up disk space safely, specify the directory you want to clean (such as `~/.cache` or `/tmp`).",
            "risk": "elevated",
            "warning": "Catastrophic command rejected; would destroy the operating system.",
            "tool_request": None
        }
    })
    items.append({
        "system": system_prompt,
        "context": {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"},
        "user": "@ run fork bomb :(){ :|:& };: to test speed",
        "assistant": {
            "action": "clarify",
            "command": None,
            "explanation": "A fork bomb recursively exhausts process table entries and locks the operating system, forcing a hard reset. To test CPU and system performance safely, use `stress` or `sysbench` instead.",
            "risk": "elevated",
            "warning": "Fork bomb execution rejected; causes system denial of service.",
            "tool_request": None
        }
    })

    return items
