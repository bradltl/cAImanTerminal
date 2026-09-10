#!/usr/bin/env python3
"""
Generate cAIman Terminal v5 Master Dataset.

Parameters:
1. Retain all ~433 v2 training examples (converted to clean schema without tool_request).
2. Add only ~20 targeted clarification examples (missing required identifiers).
3. Add ~25 multi-turn / context-aware examples.
4. Add ~21 syntax, quoting, whitespace, and command typo repair examples.
5. Avoid duplicating near-identical safety/clarification examples.
6. Keep destructive safety mostly out of SFT (host gate owns that).
"""

import json
import random
import subprocess
from pathlib import Path
from collections import Counter

OUTPUT_DIR = Path("training_dataset_v5")
SAMPLES_DIR = OUTPUT_DIR / "samples"
V2_TRAIN_FILE = Path("training_dataset_v2/trl_train.jsonl")
V2_EVAL_FILE = Path("training_dataset_v2/trl_eval.jsonl")

SYSTEM_PROMPT = (
    "You are an embedded local Linux terminal AI assistant for an interactive terminal emulator. "
    "Target environment: Arch Linux / CachyOS with Bash. "
    "Classify risk accurately, warn on elevated operations, and when arguments are missing, output action 'clarify'."
)

def check_bash_syntax(cmd: str) -> bool:
    if not cmd:
        return True
    res = subprocess.run(["bash", "-n", "-c", cmd], capture_output=True, text=True)
    return res.returncode == 0

def format_user_content(context: dict, user_text: str) -> str:
    os_name = context.get("os", "cachyos")
    shell_name = context.get("shell", "bash")
    cwd = context.get("cwd", "/home/brad")
    return (
        f"[SYSTEM CONTEXT]\n"
        f"OS: {os_name} (arch)\n"
        f"Shell: {shell_name}\n"
        f"CWD: {cwd}\n\n"
        f"[USER REQUEST]\n"
        f"{user_text}\n\n"
        f"Respond in structured JSON according to the contract:"
    )

def clean_v2_sample(s: dict) -> dict:
    """Normalize a v2 sample to the strict schema without tool_request."""
    asst = s["assistant"]
    act = asst.get("action", "suggest_command")
    cmd = asst.get("command")
    
    if act == "lookup_help":
        tr = asst.get("tool_request", {})
        if tr:
            c = tr.get("command", "")
            args = tr.get("args", [])
            if tr.get("provider") == "bash_help":
                cmd = f"help {args[0]}" if args else f"help {c}"
            elif tr.get("provider") == "man":
                cmd = f"man {c}"
            else:
                cmd = f"{c} {' '.join(args)}"
            act = "suggest_command"
            risk = "normal"
        else:
            act = "explain"
            risk = "normal"
    else:
        risk = asst.get("risk")

    clean_asst = {
        "action": act,
        "command": cmd,
        "commands": asst.get("commands"),
        "explanation": asst.get("explanation"),
        "risk": risk,
        "warning": asst.get("warning"),
        "question": asst.get("question"),
    }
    
    context = s.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"})
    user_text = s["user"]
    user_content = format_user_content(context, user_text)
    asst_content = json.dumps(clean_asst, indent=2)

    return {
        "system": SYSTEM_PROMPT,
        "context": context,
        "user": user_text,
        "assistant": clean_asst,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": asst_content},
        ]
    }

# ── 1. Targeted Clarification Examples (~20) ──────────────────────────

CLARIFICATION_EXAMPLES = [
    {
        "user": "kill -9",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Process ID (PID) argument is missing.",
            "risk": "caution", "warning": None,
            "question": "Which process ID (PID) do you want to terminate? (Find PIDs with 'ps aux | grep <name>' or 'pgrep <name>')"
        }
    },
    {
        "user": "docker logs -f",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Container name or ID is missing.",
            "risk": "normal", "warning": None,
            "question": "Which container name or ID do you want to view logs for? (Run 'docker ps' to see running containers)"
        }
    },
    {
        "user": "kubectl logs -f",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Pod name is required to stream logs.",
            "risk": "normal", "warning": None,
            "question": "Which pod name would you like to stream logs from? (Run 'kubectl get pods')"
        }
    },
    {
        "user": "gh pr checkout",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Pull request number or branch was not provided.",
            "risk": "caution", "warning": None,
            "question": "Which pull request number or branch do you want to check out? (Run 'gh pr list')"
        }
    },
    {
        "user": "aws ec2 stop-instances --instance-ids",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "The --instance-ids parameter requires one or more EC2 instance IDs.",
            "risk": "caution", "warning": None,
            "question": "Which EC2 instance ID(s) do you want to stop? (e.g. i-0123456789abcdef0)"
        }
    },
    {
        "user": "az vm restart --resource-group prod --name",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "The --name parameter requires an Azure virtual machine name.",
            "risk": "caution", "warning": None,
            "question": "Which VM name in resource group 'prod' do you want to restart?"
        }
    },
    {
        "user": "gcloud run services describe api --region",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "The --region flag requires a GCP region argument.",
            "risk": "normal", "warning": None,
            "question": "Which region is the Cloud Run service in? (e.g. us-central1, europe-west1)"
        }
    },
    {
        "user": "@ revert my changes",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Clarification needed: whether to discard unstaged working tree changes or revert a specific commit.",
            "risk": "caution", "warning": None,
            "question": "Would you like to discard unstaged working tree changes ('git restore .') or revert a specific commit ('git revert <commit>')?"
        }
    },
    {
        "user": "@ switch default gcp project",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "GCP project ID was not specified. Run `gcloud projects list` to view accessible projects.",
            "risk": "caution", "warning": None,
            "question": "Which GCP project ID would you like to set as default? Run 'gcloud projects list' to view available projects."
        }
    },
    {
        "user": "@ delete the branch",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Branch name was not specified.",
            "risk": "caution", "warning": None,
            "question": "Which branch would you like to delete? (Run 'git branch' to view local branches.)"
        }
    },
    {
        "user": "@ clear the cache",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Multiple caches exist on Linux.",
            "risk": "caution", "warning": None,
            "question": "Which cache would you like to clear: package cache ('sudo paccache -rk2') or user cache ('rm -rf ~/.cache/*')?"
        }
    },
    {
        "user": "@ restart the service",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Service unit name was not specified (e.g. `sudo systemctl restart nginx`).",
            "risk": "elevated", "warning": None,
            "question": "Which systemd service unit would you like to restart?"
        }
    },
    {
        "user": "@ stop the ec2 instance",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "EC2 instance ID is required.",
            "risk": "caution", "warning": None,
            "question": "What is the EC2 instance ID? (Run 'aws ec2 describe-instances' to list instances.)"
        }
    },
    {
        "user": "@ download file from s3",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "S3 bucket URI and destination path are needed.",
            "risk": "normal", "warning": None,
            "question": "What is the S3 object path (s3://bucket/key) and destination folder?"
        }
    },
    {
        "user": "@ ssh into compute instance",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Instance name and zone are required (e.g. `gcloud compute ssh <instance> --zone=<zone>`).",
            "risk": "normal", "warning": None,
            "question": "What is the instance name and zone? (Run 'gcloud compute instances list' to view running VMs.)"
        }
    },
    {
        "user": "systemctl status",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Service unit name was not specified.",
            "risk": "normal", "warning": None,
            "question": "Which service or systemd unit do you want to inspect? (e.g. 'systemctl status nginx' or 'systemctl status docker')"
        }
    },
    {
        "user": "docker rm",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Container name or ID is required for removal.",
            "risk": "caution", "warning": None,
            "question": "Which container do you want to remove? (Run 'docker ps -a' to list containers)"
        }
    },
    {
        "user": "kubectl describe pod",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Pod name argument is missing.",
            "risk": "normal", "warning": None,
            "question": "Which pod would you like to describe? (Run 'kubectl get pods' to list pods in current namespace)"
        }
    },
    {
        "user": "gcloud compute instances stop",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Instance name is required.",
            "risk": "caution", "warning": None,
            "question": "Which compute instance name would you like to stop? (Run 'gcloud compute instances list')"
        }
    },
    {
        "user": "@ delete the old release",
        "assistant": {
            "action": "clarify",
            "command": None, "commands": None,
            "explanation": "Release tag was not specified. Run `gh release list` to view published releases.",
            "risk": "caution", "warning": None,
            "question": "Which GitHub release tag do you want to delete? Run 'gh release list' to view existing releases."
        }
    }
]

# ── 2. Multi-turn / Context-Aware Examples (~25) ──────────────────────

CONTEXT_EXAMPLES = [
    {
        "user": "@ continue",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/project",
            "history": [
                {"command": "git stash", "exit_code": 0, "output": "Saved working directory and index state WIP on main"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git stash pop",
            "commands": None, "explanation": "Restores the stashed working directory changes.",
            "risk": "caution", "warning": "Applies and drops the most recent stash entry.",
            "question": None
        }
    },
    {
        "user": "@ continue, push to remote",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/project",
            "history": [
                {"command": "git checkout -b feature/login", "exit_code": 0, "output": "Switched to a new branch 'feature/login'"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git push -u origin feature/login",
            "commands": None, "explanation": "Pushes the newly created branch to origin and sets upstream tracking.",
            "risk": "caution", "warning": "Pushes branch 'feature/login' to remote.",
            "question": None
        }
    },
    {
        "user": "@ continue, inspect /var",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "du -sh /* | sort -h", "exit_code": 0, "output": "1.2G /home\n3.8G /usr\n12G /var"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "du -sh /var/* | sort -h",
            "commands": None, "explanation": "Inspects size of directories inside /var to find what is consuming 12GB of disk.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ fix this push error",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/repo",
            "history": [
                {"command": "git push origin main", "exit_code": 1, "output": "! [rejected] main -> main (non-fast-forward)\nhint: Updates were rejected because the remote contains work"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git pull --rebase origin main",
            "commands": None, "explanation": "Fetches remote changes and replays local commits on top to resolve non-fast-forward push.",
            "risk": "caution", "warning": "Rebases local commits on top of origin/main.",
            "question": None
        }
    },
    {
        "user": "@ fix this error",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/app",
            "history": [
                {"command": "python3 main.py", "exit_code": 1, "output": "ModuleNotFoundError: No module named 'requests'"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "pip install requests",
            "commands": None, "explanation": "Installs the missing 'requests' HTTP library in the active environment.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ diagnose port conflict",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "sudo systemctl start nginx", "exit_code": 1, "output": "nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "ss -tlnp | grep :80",
            "commands": None, "explanation": "Finds which process is currently listening on port 80 and holding the socket.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ resolve missing package",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/web",
            "history": [
                {"command": "npm run dev", "exit_code": 1, "output": "Error: Cannot find module 'dotenv'"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "npm install dotenv",
            "commands": None, "explanation": "Installs the missing 'dotenv' package into local node_modules.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ resolve missing library",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/rust-app",
            "history": [
                {"command": "cargo build", "exit_code": 101, "output": "/usr/bin/ld: cannot find -lssl: No such file or directory\ncollect2: error: ld returned 1 exit status"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "sudo pacman -S openssl",
            "commands": None, "explanation": "Installs OpenSSL development libraries required for linking.",
            "risk": "elevated", "warning": "Installs openssl system package via pacman.",
            "question": None
        }
    },
    {
        "user": "@ read this file",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "cat /etc/shadow", "exit_code": 1, "output": "cat: /etc/shadow: Permission denied"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "sudo cat /etc/shadow",
            "commands": None, "explanation": "Reads privileged /etc/shadow file using sudo.",
            "risk": "elevated", "warning": "Requires sudo privileges to view system password hashes.",
            "question": None
        }
    },
    {
        "user": "@ extract this archive",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/downloads",
            "history": [
                {"command": "ls -l", "exit_code": 0, "output": "-rw-r--r-- 1 brad brad 45M Sep 9 10:00 backup.tar.gz"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "tar -xzf backup.tar.gz",
            "commands": None, "explanation": "Extracts gzip-compressed tar archive backup.tar.gz into current directory.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ discard changes to config.yaml",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/repo",
            "history": [
                {"command": "git status", "exit_code": 0, "output": "Changes not staged for commit:\n  modified: config.yaml"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git restore config.yaml",
            "commands": None, "explanation": "Discards uncommitted working tree changes in config.yaml.",
            "risk": "caution", "warning": "Overwrites local modifications in config.yaml.",
            "question": None
        }
    },
    {
        "user": "@ inspect logs for this container",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "docker ps", "exit_code": 0, "output": "CONTAINER ID   IMAGE   NAMES\nabc123def456   redis   redis-server"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "docker logs -f redis-server",
            "commands": None, "explanation": "Follows the stdout/stderr log stream for container redis-server.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ bring up the interface",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "ip link show eth0", "exit_code": 0, "output": "2: eth0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "sudo ip link set eth0 up",
            "commands": None, "explanation": "Activates network interface eth0.",
            "risk": "elevated", "warning": "Changes network link state using sudo.",
            "question": None
        }
    },
    {
        "user": "@ install it",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad",
            "history": [
                {"command": "pacman -Ss ripgrep", "exit_code": 0, "output": "extra/ripgrep 14.1.0-1\n    line-oriented search tool"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "sudo pacman -S ripgrep",
            "commands": None, "explanation": "Installs ripgrep from the official extra repository.",
            "risk": "elevated", "warning": "Installs ripgrep system-wide via pacman.",
            "question": None
        }
    },
    {
        "user": "@ rerun failed jobs for run 98765432",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/repo",
            "history": [
                {"command": "gh run list --status failure", "exit_code": 0, "output": "failure  CI  Build  98765432"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "gh run rerun 98765432 --failed",
            "commands": None, "explanation": "Reruns only failed jobs for GitHub Actions workflow run 98765432.",
            "risk": "caution", "warning": "Triggers re-execution of failed CI workflow jobs.",
            "question": None
        }
    },
    {
        "user": "@ switch to branch bugfix/nav",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/repo",
            "history": [
                {"command": "git branch -a", "exit_code": 0, "output": "* main\n  bugfix/nav\n  remotes/origin/bugfix/nav"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git switch bugfix/nav",
            "commands": None, "explanation": "Switches the active working tree branch to bugfix/nav.",
            "risk": "caution", "warning": "Changes active Git branch.",
            "question": None
        }
    },
    {
        "user": "@ start the services in background",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/compose-app",
            "history": [
                {"command": "docker compose build", "exit_code": 0, "output": "Successfully built images"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "docker compose up -d",
            "commands": None, "explanation": "Starts containers declared in docker-compose.yml in detached background mode.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ check cpu and memory usage",
        "assistant": {
            "action": "suggest_command", "command": "htop",
            "commands": None, "explanation": "Launches interactive process viewer displaying per-core CPU and RAM metrics.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ check filesystem disk usage",
        "assistant": {
            "action": "suggest_command", "command": "df -h",
            "commands": None, "explanation": "Displays available and used disk space on all mounted filesystems in human-readable format.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ test dns resolution for google.com",
        "assistant": {
            "action": "suggest_command", "command": "dig google.com",
            "commands": None, "explanation": "Performs DNS lookup query for google.com to verify nameserver responses.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ push changes to current tracking branch",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/repo",
            "history": [
                {"command": "git commit -m 'fix: validation'", "exit_code": 0, "output": "[main a1b2c3d] fix: validation"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "git push",
            "commands": None, "explanation": "Pushes new commits to the configured remote tracking branch.",
            "risk": "caution", "warning": "Publishes commits to remote repository.",
            "question": None
        }
    },
    {
        "user": "@ reload nginx configuration",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/etc/nginx",
            "history": [
                {"command": "sudo nginx -t", "exit_code": 0, "output": "nginx: configuration file /etc/nginx/nginx.conf test is successful"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "sudo systemctl reload nginx",
            "commands": None, "explanation": "Reloads Nginx configuration without dropping active connections.",
            "risk": "elevated", "warning": "Reloads active Nginx web server process via systemctl.",
            "question": None
        }
    },
    {
        "user": "@ check if service is listening on port 8000",
        "assistant": {
            "action": "suggest_command", "command": "ss -tlnp | grep :8000",
            "commands": None, "explanation": "Queries TCP listening sockets to see if any process is bound to port 8000.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ view crash backtrace",
        "context": {
            "os": "cachyos", "shell": "bash", "cwd": "/home/brad/app",
            "history": [
                {"command": "./server", "exit_code": 139, "output": "Segmentation fault (core dumped)"}
            ]
        },
        "assistant": {
            "action": "suggest_command", "command": "coredumpctl info",
            "commands": None, "explanation": "Displays recorded core dump metadata and crash stack trace from systemd-coredump.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ remove dangling images",
        "assistant": {
            "action": "suggest_command", "command": "docker image prune -f",
            "commands": None, "explanation": "Removes untagged, dangling Docker images to reclaim disk space.",
            "risk": "caution", "warning": "Deletes untagged Docker image layers.",
            "question": None
        }
    }
]

# ── 3. Syntax / Quoting / Whitespace / Typo Repair Examples (~21) ──────

SYNTAX_EXAMPLES = [
    {
        "user": '@ view lines in file "Monthly Reports/Jan 2026.csv"',
        "assistant": {
            "action": "suggest_command", "command": 'cat "Monthly Reports/Jan 2026.csv"',
            "commands": None, "explanation": "Views file content preserving directory and filename spaces with double quotes.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": '@ delete everything inside "temp files/"',
        "assistant": {
            "action": "suggest_command", "command": 'rm -rf "temp files/"*',
            "commands": None, "explanation": "Deletes directory contents quoting path with embedded spaces.",
            "risk": "elevated", "warning": "Deletes all files inside 'temp files/'.",
            "question": None
        }
    },
    {
        "user": "@ find all log files recursively without shell expansion",
        "assistant": {
            "action": "suggest_command", "command": 'find . -name "*.log"',
            "commands": None, "explanation": "Quotes the wildcard pattern so find performs matching rather than premature shell glob expansion.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ print first and last column of access log",
        "assistant": {
            "action": "suggest_command", "command": "awk '{print $1, $NF}' /var/log/nginx/access.log",
            "commands": None, "explanation": "Uses single quotes to pass awk script and prevent shell parameter expansion of dollar signs.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ replace 127.0.0.1 with 10.0.0.1 in config.ini",
        "assistant": {
            "action": "suggest_command", "command": "sed -i 's/127\\.0\\.0\\.1/10.0.0.1/g' config.ini",
            "commands": None, "explanation": "Performs in-place replacement with sed quoting the substitution expression.",
            "risk": "caution", "warning": "Modifies config.ini in place.",
            "question": None
        }
    },
    {
        "user": "@ extract id fields from json array",
        "assistant": {
            "action": "suggest_command", "command": "jq -r '.data[].id' response.json",
            "commands": None, "explanation": "Parses JSON and outputs raw unquoted id values using jq.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ send post request with json body status ok",
        "assistant": {
            "action": "suggest_command",
            "command": "curl -X POST -H \"Content-Type: application/json\" -d '{\"status\": \"ok\"}' http://localhost:8080/health",
            "commands": None, "explanation": "Sends HTTP POST request with appropriate JSON header and properly quoted JSON body payload.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": '@ search for text "API_KEY = " in src directory',
        "assistant": {
            "action": "suggest_command", "command": 'grep -rn "API_KEY = " src/',
            "commands": None, "explanation": "Quotes search string containing spaces and equals signs.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ list open bug issues authored by me",
        "assistant": {
            "action": "suggest_command", "command": 'gh issue list --search "label:bug is:open author:@me"',
            "commands": None, "explanation": "Queries GitHub issues filtering by bug label and authenticated author with quotes.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "@ list running compute instances in us-central1",
        "assistant": {
            "action": "suggest_command", "command": 'gcloud compute instances list --filter="status=RUNNING AND zone:us-central1"',
            "commands": None, "explanation": "Applies compound filter expression to gcloud CLI command with quotes.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "gti status",
        "assistant": {
            "action": "suggest_command", "command": "git status",
            "commands": None, "explanation": "Corrects typo 'gti' to 'git status'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "kubeclt get nodes",
        "assistant": {
            "action": "suggest_command", "command": "kubectl get nodes",
            "commands": None, "explanation": "Corrects typo 'kubeclt' to 'kubectl get nodes'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "docekr ps",
        "assistant": {
            "action": "suggest_command", "command": "docker ps",
            "commands": None, "explanation": "Corrects typo 'docekr' to 'docker ps'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "systemclt restart nginx",
        "assistant": {
            "action": "suggest_command", "command": "sudo systemctl restart nginx",
            "commands": None, "explanation": "Corrects typo 'systemclt' to 'systemctl' and includes sudo elevation.",
            "risk": "elevated", "warning": "Restarts nginx service using sudo.",
            "question": None
        }
    },
    {
        "user": "pyhton3 app.py",
        "assistant": {
            "action": "suggest_command", "command": "python3 app.py",
            "commands": None, "explanation": "Corrects typo 'pyhton3' to 'python3 app.py'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "crl -I https://example.com",
        "assistant": {
            "action": "suggest_command", "command": "curl -I https://example.com",
            "commands": None, "explanation": "Corrects typo 'crl' to 'curl -I'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "pakman -Syu",
        "assistant": {
            "action": "suggest_command", "command": "sudo pacman -Syu",
            "commands": None, "explanation": "Corrects typo 'pakman' to 'pacman' and adds required sudo.",
            "risk": "elevated", "warning": "Updates Arch Linux package database and system packages.",
            "question": None
        }
    },
    {
        "user": 'grpe -rn "TODO" .',
        "assistant": {
            "action": "suggest_command", "command": 'grep -rn "TODO" .',
            "commands": None, "explanation": "Corrects typo 'grpe' to 'grep'.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "chmdo +x run.sh",
        "assistant": {
            "action": "suggest_command", "command": "chmod +x run.sh",
            "commands": None, "explanation": "Corrects typo 'chmdo' to 'chmod +x run.sh'.",
            "risk": "caution", "warning": "Grants executable permissions to run.sh.",
            "question": None
        }
    },
    {
        "user": "grep --recursivee pattern .",
        "assistant": {
            "action": "suggest_command", "command": "grep -r pattern .",
            "commands": None, "explanation": "Corrects invalid flag '--recursivee' to '-r' for recursive directory search.",
            "risk": "normal", "warning": None, "question": None
        }
    },
    {
        "user": "dockr compose up -d",
        "assistant": {
            "action": "suggest_command", "command": "docker compose up -d",
            "commands": None, "explanation": "Corrects typo 'dockr' to 'docker compose up -d'.",
            "risk": "normal", "warning": None, "question": None
        }
    }
]

def main():
    print("=== Generating cAIman Terminal v5 Dataset ===")
    
    # 1. Load v2 dataset
    v2_samples = []
    with open("training_dataset_v2/dataset.jsonl") as f:
        for line in f:
            v2_samples.append(json.loads(line))
    print(f"Loaded v2 master dataset: {len(v2_samples)} samples")

    master_dict = {}

    # Add all v2 samples (normalized to clean schema without tool_request)
    for raw in v2_samples:
        cleaned = clean_v2_sample(raw)
        key = cleaned["user"].strip().lower()
        master_dict[key] = cleaned

    print(f"Cleaned v2 samples in dict: {len(master_dict)}")

    # 2. Add targeted clarification examples (~20)
    clar_added = 0
    for ex in CLARIFICATION_EXAMPLES:
        key = ex["user"].strip().lower()
        context = ex.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"})
        user_text = ex["user"]
        user_content = format_user_content(context, user_text)
        asst_content = json.dumps(ex["assistant"], indent=2)
        master_dict[key] = {
            "system": SYSTEM_PROMPT,
            "context": context,
            "user": user_text,
            "assistant": ex["assistant"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": asst_content},
            ]
        }
        clar_added += 1
    print(f"Integrated clarification examples: {clar_added}")

    # 3. Add multi-turn / context examples (~25)
    ctx_added = 0
    for ex in CONTEXT_EXAMPLES:
        key = ex["user"].strip().lower()
        context = ex.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"})
        user_text = ex["user"]
        user_content = format_user_content(context, user_text)
        asst_content = json.dumps(ex["assistant"], indent=2)
        master_dict[key] = {
            "system": SYSTEM_PROMPT,
            "context": context,
            "user": user_text,
            "assistant": ex["assistant"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": asst_content},
            ]
        }
        ctx_added += 1
    print(f"Integrated context / multi-turn examples: {ctx_added}")

    # 4. Add syntax / quoting / typo examples (~21)
    syn_added = 0
    for ex in SYNTAX_EXAMPLES:
        key = ex["user"].strip().lower()
        context = ex.get("context", {"os": "cachyos", "shell": "bash", "cwd": "/home/brad"})
        user_text = ex["user"]
        user_content = format_user_content(context, user_text)
        asst_content = json.dumps(ex["assistant"], indent=2)
        master_dict[key] = {
            "system": SYSTEM_PROMPT,
            "context": context,
            "user": user_text,
            "assistant": ex["assistant"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": asst_content},
            ]
        }
        syn_added += 1
    print(f"Integrated syntax / quoting / typo examples: {syn_added}")

    # Convert to ordered list & shuffle
    dataset = list(master_dict.values())
    random.seed(42)
    random.shuffle(dataset)

    print(f"\nTotal v5 dataset size: {len(dataset)} samples")

    # Clean and write
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    for old_f in SAMPLES_DIR.glob("*.json"):
        old_f.unlink()

    for idx, sample in enumerate(dataset, 1):
        sample_path = SAMPLES_DIR / f"sample_{idx:04d}.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "dataset.jsonl", "w", encoding="utf-8") as f:
        for s in dataset:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    split_idx = int(len(dataset) * 0.90)
    train_samples = dataset[:split_idx]
    eval_samples = dataset[split_idx:]

    with open(OUTPUT_DIR / "trl_train.jsonl", "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(OUTPUT_DIR / "trl_eval.jsonl", "w", encoding="utf-8") as f:
        for s in eval_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    actions = Counter(s["assistant"]["action"] for s in dataset)
    risks = Counter(s["assistant"]["risk"] for s in dataset)

    summary = {
        "dataset_name": "cayman-terminal-v5-balanced",
        "total_examples": len(dataset),
        "train_examples": len(train_samples),
        "eval_examples": len(eval_samples),
        "parameters": [
            "retain all v2 multi-domain breadth (~482 dataset / 433 train samples)",
            "add ~20 high-value clarification examples (missing required identifiers)",
            "add ~25 multi-turn / context-aware examples",
            "add ~21 syntax / quoting / whitespace / typo repair examples",
            "zero tool_request in assistant responses",
            "destructive safety left out of SFT (host gate owns destructive bounds)"
        ],
        "action_distribution": dict(actions),
        "risk_distribution": dict(risks),
    }

    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✔ Successfully generated {len(dataset)} samples ({len(train_samples)} train, {len(eval_samples)} eval)")
    print(f"  Actions: {dict(actions)}")
    print(f"  Risks:   {dict(risks)}")
    print(f"  Saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
