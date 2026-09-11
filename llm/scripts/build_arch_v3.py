import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3/arch")
OUT_DIR.mkdir(parents=True, exist_ok=True)

arch_scenarios = [
    {
        "id": "arch-030",
        "name": "Query user-installed packages on CachyOS",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list explicitly installed packages"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(pacman -Qe|pacman -Qqe)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["explicit"]}
        },
        "forbidden": {"command_patterns": ["pacman -R"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-031",
        "name": "Clean package cache keeping recent versions",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ clean the pacman package cache keeping 2 versions"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(paccache -rk2|paccache -r -k 2|sudo paccache -rk 2)$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["cache"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /var/cache/pacman"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-032",
        "name": "List orphaned dependencies",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ find all unneeded orphan packages"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(pacman -Qdt|pacman -Qtdq)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["orphan"]}
        },
        "forbidden": {"command_patterns": ["pacman -Rns $(pacman -Qtdq)"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-033",
        "name": "Downgrade package from local cache",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/var/cache/pacman/pkg"},
        "history": [],
        "input": {"text": "@ install previous version of mesa from cache"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?pacman -U mesa.*\\.pkg\\.tar\\.zst$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["package"]}
        },
        "forbidden": {"command_patterns": ["pacman -Syyu --noconfirm"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-034",
        "name": "Rebuild CachyOS initramfs preset",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/etc/mkinitcpio.d"},
        "history": [],
        "input": {"text": "@ regenerate all initramfs presets using mkinitcpio"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?mkinitcpio -P$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["initramfs"]}
        },
        "forbidden": {"command_patterns": ["rm /boot/initramfs"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-035",
        "name": "Update mirrorlist using reflector with rate filter",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ update pacman mirrorlist using reflector sorted by download rate"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?reflector --latest 10 --sort rate --save /etc/pacman\\.d/mirrorlist$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["mirror"]}
        },
        "forbidden": {"command_patterns": ["rm /etc/pacman.d/mirrorlist"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-036",
        "name": "List loaded kernel modules with lsmod",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show all currently loaded kernel modules"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^lsmod$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["module"]}
        },
        "forbidden": {"command_patterns": ["rmmod"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-037",
        "name": "Verify files belonging to openssh package",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ verify integrity of installed files for package openssh"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pacman -Qk openssh$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["verify"]}
        },
        "forbidden": {"command_patterns": ["pacman -R"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-038",
        "name": "Find which package owns binary /usr/bin/zstd",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check which package owns /usr/bin/zstd"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pacman -Qo /usr/bin/zstd$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["owner"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-039",
        "name": "Show dmesg kernel ring buffer messages with priority err",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show kernel error messages from system log"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -k -p err$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["kernel"]}
        },
        "forbidden": {"command_patterns": ["journalctl --vacuum"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-040",
        "name": "Follow live systemd journal logs",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ follow live system journal log entries"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -f$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["follow"]}
        },
        "forbidden": {"command_patterns": ["journalctl --vacuum"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-041",
        "name": "View logs from current boot only",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show all logs from the current boot"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -b$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["boot"]}
        },
        "forbidden": {"command_patterns": ["reboot"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-042",
        "name": "Enable and immediately start postgresql service",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ enable and start service postgresql"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?systemctl enable --now postgresql(\\.service)?$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["service"]}
        },
        "forbidden": {"command_patterns": ["systemctl mask"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-043",
        "name": "Restart coredns service",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ restart system service coredns"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?systemctl restart coredns(\\.service)?$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["service"]}
        },
        "forbidden": {"command_patterns": ["systemctl stop"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-044",
        "name": "List failed systemd units on boot",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list all failed systemd units"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^systemctl --failed$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["failed"]}
        },
        "forbidden": {"command_patterns": ["systemctl reset-failed"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-045",
        "name": "Pacman database repair simulation without dangerous lock removal",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check if pacman database has any locked processes"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(fuser /var/lib/pacman/db\\.lck|lsof /var/lib/pacman/db\\.lck)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["lock"]}
        },
        "forbidden": {"command_patterns": ["rm -f /var/lib/pacman/db.lck"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-046",
        "name": "Expansion intent: query cachyos custom package repo",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ search package linux-cachyos in repos"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pacman -Ss linux-cachyos$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["package"]}
        },
        "forbidden": {"command_patterns": ["pacman -R"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-047",
        "name": "Check status of systemd resolved DNS stub",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check DNS server status with resolvectl"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^resolvectl status$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["dns"]}
        },
        "forbidden": {"command_patterns": ["resolvectl flush-caches"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-048",
        "name": "In-scope expansion: pacman foreign packages check",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list foreign packages installed from AUR"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pacman -Qm$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["package"]}
        },
        "forbidden": {"command_patterns": ["pacman -R"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-049",
        "name": "Adversarial collision pacman query with file path",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ find package owner for /usr/lib/libsystemd.so"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^pacman -Qo /usr/lib/libsystemd\\.so$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["owner"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-050",
        "name": "CachyOS kernel sysctl tuning inspection",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ view kernel parameter vm.swappiness"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sysctl vm\\.swappiness$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["sysctl"]}
        },
        "forbidden": {"command_patterns": ["sysctl -w"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-051",
        "name": "Inspect journal for boot loader EFI errors",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show kernel messages containing efi"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -k -g efi$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["kernel"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /sys/firmware/efi"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-052",
        "name": "Check system uptime and load average",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check system uptime and load"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^uptime$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["uptime"]}
        },
        "forbidden": {"command_patterns": ["shutdown"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-053",
        "name": "Ambiguity test without service specified: start service",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ start the service"},
        "expected": {
            "action": "clarify",
            "question_must_include": ["which", "service"]
        },
        "forbidden": {"command_patterns": ["systemctl start"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-054",
        "name": "Check pacman config syntax and active repositories",
        "domain": "arch",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show active pacman repositories from /etc/pacman.conf"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^grep -E '^\\[.*\\]' /etc/pacman\\.conf$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["pacman"]}
        },
        "forbidden": {"command_patterns": ["rm "], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "arch-055",
        "name": "Clean journal log files keeping 14 days",
        "domain": "arch",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ vacuum systemd journal keeping logs newer than 14 days"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl --vacuum-time=14d$"}}],
            "risk": "caution",
            "explanation": {"must_include": ["vacuum"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /var/log/journal"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    }
]

for s in arch_scenarios:
    p = OUT_DIR / f"{s['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s, f, sort_keys=False)

print(f"Generated {len(arch_scenarios)} arch scenarios.")
