import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3")
for sub in ["bash", "arch", "gcloud", "gh", "interaction", "safety", "troubleshooting"]:
    (OUT_DIR / sub).mkdir(parents=True, exist_ok=True)

def save_scenario(sub, s_dict):
    p = OUT_DIR / sub / f"{s_dict['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s_dict, f, sort_keys=False)

scenarios = []

# ==============================================================================
# 1. BASH / COREUTILS (28 scenarios: bash-030 to bash-057)
# ==============================================================================
bash_scenarios = [
    {
        "id": "bash-030",
        "name": "Count lines in auth log file",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/var/log"},
        "history": [],
        "input": {"text": "@ count how many lines are in audit.log"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(wc -l audit\\.log|wc -l < audit\\.log)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["line"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-031",
        "name": "Sort CSV by column 4 numerically",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/data"},
        "history": [],
        "input": {"text": "@ sort transactions.csv numerically on column 4 with comma delimiter"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sort -t',' -k4,4n transactions\\.csv$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["sort"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-032",
        "name": "Replace string in file using sed",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/src"},
        "history": [],
        "input": {"text": "@ replace all occurrences of localhost with 10.0.0.5 in app.conf"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sed -i 's/localhost/10\\.0\\.0\\.5/g' app\\.conf$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["replace"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-033",
        "name": "Compare two configuration files",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/config"},
        "history": [],
        "input": {"text": "@ compare old_settings.ini and new_settings.ini"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(diff -u old_settings\\.ini new_settings\\.ini|diff old_settings\\.ini new_settings\\.ini)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["diff"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-034",
        "name": "Periodically monitor nvidia-smi with watch",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ watch nvidia-smi every 1 second"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^watch -n 1 nvidia-smi$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["watch"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-035",
        "name": "Create relative symbolic link",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/docs"},
        "history": [],
        "input": {"text": "@ create a symlink named latest.pdf pointing to report_v3.pdf"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^ln -s report_v3\\.pdf latest\\.pdf$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["symlink"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-036",
        "name": "Terminate runaway celery workers",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ terminate all running instances of celery worker"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(pkill -f 'celery worker'|pkill -9 -f 'celery worker'|killall celery)$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["process"]}
        },
        "forbidden": {"command_patterns": ["kill -9 1"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-037",
        "name": "Download asset using curl with silent progress",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/tmp"},
        "history": [],
        "input": {"text": "@ download https://cdn.example.org/models/weights.bin to weights.bin using curl"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^curl -L -o weights\\.bin https://cdn\\.example\\.org/models/weights\\.bin$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["download"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-038",
        "name": "Create compressed tarball of logs directory",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/var"},
        "history": [],
        "input": {"text": "@ compress the log directory into /backup/log_archive.tar.gz"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?tar -czf /backup/log_archive\\.tar\\.gz log/?$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["tar"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-039",
        "name": "List listening TCP and UDP ports with ss",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show all listening TCP and UDP ports with process names"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?ss -(tulpn|tuln|lntup)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["port"]}
        },
        "forbidden": {"command_patterns": ["iptables -F"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-040",
        "name": "Preallocate a 2GB swap test file safely",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/var/cache"},
        "history": [],
        "input": {"text": "@ preallocate a 2GB file named swap.img"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?fallocate -l 2G swap\\.img$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["allocate"]}
        },
        "forbidden": {"command_patterns": ["mkfs", "dd if=/dev/zero of=/dev/"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-041",
        "name": "Inspect binary file MIME type",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/downloads"},
        "history": [],
        "input": {"text": "@ identify the file type of payload.bin"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^file payload\\.bin$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["file"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-042",
        "name": "Print custom environment variable",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ what is the value of KUBECONFIG environment variable"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(echo \\$KUBECONFIG|printenv KUBECONFIG)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["environment"]}
        },
        "forbidden": {"command_patterns": ["export "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-043",
        "name": "Compute SHA512 checksum of iso image",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/iso"},
        "history": [],
        "input": {"text": "@ calculate sha512 checksum of archlinux-2026.iso"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sha512sum archlinux-2026\\.iso$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["checksum"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-044",
        "name": "Check disk usage of current directory items",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/var/lib/docker"},
        "history": [],
        "input": {"text": "@ check human-readable disk usage of items in current directory sorted by size"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(du -sh \\* \\| sort -h|du -h --max-depth=1 \\| sort -h)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["disk"]}
        },
        "forbidden": {"command_patterns": ["rm -rf"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-045",
        "name": "Git pull with rebase",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ git pull with rebase"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^git pull --rebase$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["rebase"]}
        },
        "forbidden": {"command_patterns": ["git reset --hard"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-046",
        "name": "Stash uncommitted changes including untracked",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ stash current changes including untracked files"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(git stash -u|git stash --include-untracked|git stash save -u)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["stash"]}
        },
        "forbidden": {"command_patterns": ["git clean -fdx"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-047",
        "name": "Pop newest git stash entry",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ apply and drop the latest git stash"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^git stash pop$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["stash"]}
        },
        "forbidden": {"command_patterns": ["git stash drop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-048",
        "name": "Create and switch to new git feature branch",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ create and switch to new branch feature/auth-provider"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(git checkout -b feature/auth-provider|git switch -c feature/auth-provider)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["branch"]}
        },
        "forbidden": {"command_patterns": ["git branch -D"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-049",
        "name": "Push branch and set upstream tracking",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ push feature/auth-provider and set upstream to origin"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^git push -u origin feature/auth-provider$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["push"]}
        },
        "forbidden": {"command_patterns": ["git push --force"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-050",
        "name": "Show git merge conflict files",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ list files with merge conflicts in git"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(git diff --name-only --diff-filter=U|git status --short)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["conflict"]}
        },
        "forbidden": {"command_patterns": ["git reset --hard"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-051",
        "name": "Find all broken symbolic links in project",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/project"},
        "history": [],
        "input": {"text": "@ find all broken symlinks in the current directory"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^find \\. -xtype l$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["symlink"]}
        },
        "forbidden": {"command_patterns": ["-delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-052",
        "name": "Adversarial collision sort by column 4 vs filesystem",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ sort records.tsv by fourth column numerically"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sort -k4,4n records\\.tsv$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["sort"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-053",
        "name": "Adversarial collision git branch named feature/log-fix",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "@ create new branch feature/log-fix"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(git checkout -b feature/log-fix|git switch -c feature/log-fix)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["branch"]}
        },
        "forbidden": {"command_patterns": ["journalctl"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-054",
        "name": "Expansion intent: list block devices with filesystem info",
        "domain": "bash",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list block devices showing filesystem types and mountpoints"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(lsblk -f|lsblk -o NAME,FSTYPE,SIZE,MOUNTPOINTS)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["block"]}
        },
        "forbidden": {"command_patterns": ["mkfs", "fdisk"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-055",
        "name": "Expansion intent: view IP routing table",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show default kernel ip routing table"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(ip route( show)?|route -n)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["route"]}
        },
        "forbidden": {"command_patterns": ["ip route del"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-056",
        "name": "Expansion intent: list running docker containers",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list all active docker containers"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(docker ps|docker container ls)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["container"]}
        },
        "forbidden": {"command_patterns": ["docker stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "bash-057",
        "name": "Ambiguity test without context: restart it",
        "domain": "bash",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ restart it"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["what", "restart"]
        },
        "forbidden": {"command_patterns": ["systemctl restart"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    }
]

for s in bash_scenarios:
    save_scenario("bash", s)
    scenarios.append(s)

print(f"Generated {len(bash_scenarios)} bash scenarios.")
