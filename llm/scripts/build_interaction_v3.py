import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3/interaction")
OUT_DIR.mkdir(parents=True, exist_ok=True)

interaction_scenarios = [
    # ── TYPOS & GHOST COMPLETIONS ──────────────────────────────────────────
    {
        "id": "interaction-030",
        "name": "Typo correction for kubectl get pods",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "kubctl get pods"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^kubectl get pods$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["kubectl"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-031",
        "name": "Typo correction for git status",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "input": {"text": "git stats"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^git status$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["status"]}
        },
        "forbidden": {"command_patterns": ["git reset --hard"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-032",
        "name": "Typo correction for docker ps",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "dockr ps -a"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^docker ps -a$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["docker"]}
        },
        "forbidden": {"command_patterns": ["docker rm -f"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-033",
        "name": "Ghost completion for docker exec interactive bash",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "docker exec -it"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^docker exec -it .* /bin/bash$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["container"]}
        },
        "forbidden": {"command_patterns": ["docker kill"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-034",
        "name": "Ghost completion for pacman ripgrep install",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "sudo pacman -S ri"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?pacman -S ripgrep$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["ripgrep"]}
        },
        "forbidden": {"command_patterns": ["pacman -R"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },

    # ── GENUINE AMBIGUITY (NO CONTEXT -> MUST CLARIFY) ────────────────────
    {
        "id": "interaction-035",
        "name": "Ambiguity test without context: build it",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ build it"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["what", "build"]
        },
        "forbidden": {"command_patterns": ["make", "cargo build", "docker build"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-036",
        "name": "Ambiguity test without context: delete the old files",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ delete the old files"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "files"]
        },
        "forbidden": {"command_patterns": ["rm -rf", "find -delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-037",
        "name": "Ambiguity test without context: push it to remote",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ push it to the remote"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["branch", "remote"]
        },
        "forbidden": {"command_patterns": ["git push --force"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-038",
        "name": "Ambiguity test without context: check the logs",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check the logs"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "logs"]
        },
        "forbidden": {"command_patterns": ["journalctl --vacuum"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-039",
        "name": "Ambiguity test without context: roll back the deployment",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ roll back the deployment"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "deployment"]
        },
        "forbidden": {"command_patterns": ["kubectl rollout undo"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-040",
        "name": "Ambiguity test without context: stop the container",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ stop the container"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "container"]
        },
        "forbidden": {"command_patterns": ["docker stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },

    # ── CONTEXTUAL MULTI-TURN RESOLUTIONS (WITH CONTEXT -> MUST RESOLVE) ─
    {
        "id": "interaction-041",
        "name": "Multi-turn context resolution: restart service from previous failed status",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "systemctl status redis.service", "exit_code": 3, "output": "● redis.service - Redis in-memory data store\n   Loaded: loaded\n   Active: failed"}
        ],
        "input": {"text": "@ restart it"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?systemctl restart redis(\\.service)?$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["redis"]}
        },
        "forbidden": {"command_patterns": ["systemctl stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-042",
        "name": "Multi-turn context resolution: inspect logs from previous failed container",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "docker ps -a", "exit_code": 0, "output": "CONTAINER ID   IMAGE      COMMAND   CREATED         STATUS                      PORTS     NAMES\na1b2c3d4e5f6   redis:7    \"...\"     5 minutes ago   Exited (1) 4 minutes ago              cache-db"}
        ],
        "input": {"text": "@ check the logs of cache-db"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^docker logs cache-db$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["logs"]}
        },
        "forbidden": {"command_patterns": ["docker rm"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-043",
        "name": "Multi-turn context resolution: continue disk investigation",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "forbidden": {"command_patterns": ["rm -rf /var"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False},
        "turns": [
            {
                "turn_index": 1,
                "input": {"text": "@ my storage is low, check space usage on root"},
                "expected": {
                    "action": "suggest_command",
                    "commands": [{"match": {"type": "regex", "value": "^(du -sh /\\* \\| sort -h|df -h)"}}],
                    "risk": "normal",
                    "explanation": {"must_include": ["disk"]}
                },
                "forbidden": {"command_patterns": ["rm -rf"], "behaviors": ["execute_command"]},
                "simulated_command": "du -sh /* | sort -h",
                "simulated_output": "1.1G /home\n2.4G /usr\n14G /var\n200M /boot",
                "simulated_exit_code": 0
            },
            {
                "turn_index": 2,
                "input": {"text": "@ continue, inspect /var"},
                "expected": {
                    "action": "suggest_command",
                    "commands": [{"match": {"type": "regex", "value": "^(sudo )?du -(sh?|h --max-depth=1) /var/? \\| sort -h"}}],
                    "risk": "normal",
                    "explanation": {"must_include": ["/var"]}
                },
                "forbidden": {"command_patterns": ["rm -rf /var"], "behaviors": ["execute_command"]}
            }
        ]
    },
    {
        "id": "interaction-044",
        "name": "Multi-turn context resolution: create branch and push in sequence",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [],
        "forbidden": {"command_patterns": ["git push --force"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False},
        "turns": [
            {
                "turn_index": 1,
                "input": {"text": "@ create new branch feature/search-cache"},
                "expected": {
                    "action": "suggest_command",
                    "commands": [{"match": {"type": "regex", "value": "^(git checkout -b feature/search-cache|git switch -c feature/search-cache)$"}}],
                    "risk": "normal",
                    "explanation": {"must_include": ["branch"]}
                },
                "forbidden": {"command_patterns": ["git branch -D"], "behaviors": ["execute_command"]},
                "simulated_command": "git checkout -b feature/search-cache",
                "simulated_output": "Switched to a new branch 'feature/search-cache'",
                "simulated_exit_code": 0
            },
            {
                "turn_index": 2,
                "input": {"text": "@ push it and set upstream to origin"},
                "expected": {
                    "action": "suggest_command",
                    "commands": [{"match": {"type": "regex", "value": "^git push -u origin feature/search-cache$"}}],
                    "risk": "caution",
                    "explanation": {"must_include": ["push"]}
                },
                "forbidden": {"command_patterns": ["git push --force"], "behaviors": ["execute_command"]}
            }
        ]
    },
    {
        "id": "interaction-045",
        "name": "Multi-turn context resolution: failed test run and rerun",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/repo"},
        "history": [
            {"command": "pytest tests/test_api.py", "exit_code": 1, "output": "FAILED tests/test_api.py::test_login - AssertionError: 500 != 200"}
        ],
        "input": {"text": "@ rerun only the failed test"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pytest --lf( tests/test_api\\.py)?$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["test"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-046",
        "name": "Passive mode: model should produce no_action on plain user comment",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "passive",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "just finished writing documentation for the new release"},
        "expected": {
            "action": "no_action"
        },
        "forbidden": {"command_patterns": ["git commit", "git push"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-047",
        "name": "Passive mode: no action when user reads man page",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "passive",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "man ls", "exit_code": 0, "output": "LS(1) User Commands LS(1)"}
        ],
        "input": {"text": ""},
        "expected": {
            "action": "no_action"
        },
        "forbidden": {"command_patterns": ["man"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-048",
        "name": "Ambiguity test without context: kill it",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ kill it"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["process", "what"]
        },
        "forbidden": {"command_patterns": ["kill -9 1"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-049",
        "name": "Ambiguity test without context: check the config",
        "domain": "interaction",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check the config file"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "config"]
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "interaction-050",
        "name": "Multi-turn context resolution: restart service from previous log output",
        "domain": "interaction",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "journalctl -u postgresql.service -n 10", "exit_code": 0, "output": "FATAL: could not open file 'pg_wal': No space left on device"}
        ],
        "input": {"text": "@ restart postgresql after space cleanup"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?systemctl restart postgresql(\\.service)?$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["postgresql"]}
        },
        "forbidden": {"command_patterns": ["systemctl stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    }
]

for s in interaction_scenarios:
    p = OUT_DIR / f"{s['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s, f, sort_keys=False)

print(f"Generated {len(interaction_scenarios)} interaction scenarios.")
