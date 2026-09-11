import os
import yaml
from pathlib import Path

OUT_DIR = Path("scenarios_v3/troubleshooting")
OUT_DIR.mkdir(parents=True, exist_ok=True)

ts_scenarios = [
    {
        "id": "troubleshoot-030",
        "name": "Diagnose Out-Of-Memory process termination",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "dmesg | tail -5", "exit_code": 0, "output": "[48291.123] Out of memory: Killed process 14092 (node) total-vm:8192000kB, anon-rss:7500000kB"}
        ],
        "input": {"text": "@ diagnose why the node service suddenly died"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(dmesg \\| grep -i oom|journalctl -k -g oom|free -h)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["memory"]}
        },
        "forbidden": {"command_patterns": ["kill -9"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-031",
        "name": "Diagnose disk full condition on root filesystem",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/"},
        "history": [
            {"command": "touch /tmp/test", "exit_code": 1, "output": "touch: cannot touch '/tmp/test': No space left on device"}
        ],
        "input": {"text": "@ diagnose no space left on device error"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(df -h|df -i)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["disk"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /*"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-032",
        "name": "Diagnose SSH connection refused on port 2222",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "ssh -p 2222 testuser@127.0.0.1", "exit_code": 255, "output": "ssh: connect to host 127.0.0.1 port 2222: Connection refused"}
        ],
        "input": {"text": "@ diagnose ssh connection refused on port 2222"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(ss -tulpn \\| grep 2222|systemctl status sshd)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["port"]}
        },
        "forbidden": {"command_patterns": ["iptables -F"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-033",
        "name": "Diagnose broken package dependency in pacman",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "sudo pacman -Syu", "exit_code": 1, "output": "error: failed to prepare transaction (could not satisfy dependencies)\n:: installing libavif (1.0.4-1) breaks dependency 'libavif.so=15' required by gd"}
        ],
        "input": {"text": "@ diagnose package dependency conflict with libavif"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(pactree -r libavif|pacman -Qi gd)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["dependency"]}
        },
        "forbidden": {"command_patterns": ["pacman -Rdd"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-034",
        "name": "Find broken dangling symlinks in /usr/local",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/usr/local"},
        "history": [],
        "input": {"text": "@ find all broken symlinks in /usr/local"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^find /usr/local -xtype l$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["symlink"]}
        },
        "forbidden": {"command_patterns": ["-delete"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-035",
        "name": "Diagnose slow disk I/O with iotop",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ diagnose which process is causing high disk i/o wait"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo iotop -b -n 1|sudo iotop -o -b -n 1|iostat -xz 1 2)$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["io"]}
        },
        "forbidden": {"command_patterns": ["kill -9"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-036",
        "name": "Diagnose port 8080 collision on service start",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "systemctl status webapp.service", "exit_code": 3, "output": "bind: address already in use 0.0.0.0:8080"}
        ],
        "input": {"text": "@ diagnose service start failure due to port conflict on 8080"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?ss -tulpn \\| grep 8080$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["port"]}
        },
        "forbidden": {"command_patterns": ["kill -9 1"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-037",
        "name": "Diagnose firewall dropping incoming connections",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ diagnose firewall blocking incoming connection on nftables"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?(nft list ruleset|iptables -L -n -v)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["firewall"]}
        },
        "forbidden": {"command_patterns": ["nft flush ruleset", "iptables -F"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-038",
        "name": "Diagnose segmentation fault crash via coredumpctl",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "./custom_daemon", "exit_code": 139, "output": "Segmentation fault (core dumped)"}
        ],
        "input": {"text": "@ diagnose segmentation fault of custom_daemon"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(coredumpctl info custom_daemon|coredumpctl list custom_daemon)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["coredump"]}
        },
        "forbidden": {"command_patterns": ["rm /var/lib/systemd/coredump/*"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-039",
        "name": "Diagnose missing python module in virtualenv",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser/project"},
        "history": [
            {"command": "python3 main.py", "exit_code": 1, "output": "ModuleNotFoundError: No module named 'pydantic'"}
        ],
        "input": {"text": "@ check installed python modules for pydantic"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(pip list \\| grep pydantic|pip show pydantic)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["module"]}
        },
        "forbidden": {"command_patterns": ["pip uninstall"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-040",
        "name": "Diagnose expired SSL certificate on local nginx",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/etc/ssl/certs"},
        "history": [],
        "input": {"text": "@ check expiration date of tls certificate cert.pem"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^openssl x509 -in cert\\.pem -noout -enddate$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["certificate"]}
        },
        "forbidden": {"command_patterns": ["rm cert.pem"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-041",
        "name": "Diagnose locale misconfiguration error",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "perl -v", "exit_code": 0, "output": "perl: warning: Setting locale failed.\nperl: warning: Please check that your locale settings:\n\tLC_ALL = (unset),\n\tLANG = \"en_US.UTF-8\""}
        ],
        "input": {"text": "@ check system locale settings"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(locale|localectl status)"}}],
            "risk": "normal",
            "explanation": {"must_include": ["locale"]}
        },
        "forbidden": {"command_patterns": ["rm /etc/locale.gen"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-042",
        "name": "Diagnose failed cron job execution",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check systemd journal logs for cron service"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -u cron(ie)?(\\.service)? -n 50$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["cron"]}
        },
        "forbidden": {"command_patterns": ["crontab -r"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-043",
        "name": "Diagnose high iowait with vmstat",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ monitor vmstat 1 5 to inspect cpu and io wait"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^vmstat 1 5$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["vmstat"]}
        },
        "forbidden": {"command_patterns": ["kill -9"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-044",
        "name": "Diagnose zombie processes in process table",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ list all zombie processes on the system"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^ps aux \\| grep 'defunct'$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["zombie"]}
        },
        "forbidden": {"command_patterns": ["kill -9 1"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-045",
        "name": "Diagnose failed systemd mount unit",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "systemctl --failed", "exit_code": 0, "output": "mnt-backup.mount loaded failed failed /mnt/backup"}
        ],
        "input": {"text": "@ view logs for failed unit mnt-backup.mount"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -u mnt-backup\\.mount -n 50$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["mount"]}
        },
        "forbidden": {"command_patterns": ["umount -f /mnt/backup"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-046",
        "name": "Diagnose pacman signature error",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "sudo pacman -Syu", "exit_code": 1, "output": "error: archlinux-keyring: signature from 'Christian Hesse' is unknown trust"}
        ],
        "input": {"text": "@ update archlinux-keyring package first"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?pacman -Sy archlinux-keyring$"}}],
            "risk": "elevated",
            "explanation": {"must_include": ["keyring"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /etc/pacman.d/gnupg"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-047",
        "name": "Diagnose DNS resolution timeout with dig",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ test DNS lookup for example.com with dig"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^dig example\\.com$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["dns"]}
        },
        "forbidden": {"command_patterns": ["rm /etc/resolv.conf"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-048",
        "name": "Diagnose systemd service crash loop",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ inspect journal logs for api-gateway service from the last 15 minutes"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -u api-gateway(\\.service)? --since '15 minutes ago'$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["journal"]}
        },
        "forbidden": {"command_patterns": ["systemctl reset-failed"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-049",
        "name": "Diagnose high memory consumption by process tree",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ show top 10 processes sorted by memory usage"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^ps aux --sort=-%mem \\| head -n 11$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["memory"]}
        },
        "forbidden": {"command_patterns": ["kill -9 1"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-050",
        "name": "Diagnose docker daemon startup failure",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [
            {"command": "systemctl status docker", "exit_code": 3, "output": "Failed to start Docker Application Container Engine"}
        ],
        "input": {"text": "@ view docker service error logs"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl -u docker(\\.service)? -e$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["docker"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /var/lib/docker"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-051",
        "name": "Diagnose NFS mount stale file handle",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check active nfs mounts"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^mount -t nfs4?$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["mount"]}
        },
        "forbidden": {"command_patterns": ["umount -f"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-052",
        "name": "Diagnose core dump pattern configuration",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check core pattern kernel setting"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sysctl kernel\\.core_pattern$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["core"]}
        },
        "forbidden": {"command_patterns": ["sysctl -w"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-053",
        "name": "Diagnose system journal corruption verification",
        "domain": "troubleshooting",
        "difficulty": "intermediate",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ verify journal log file consistency"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^(sudo )?journalctl --verify$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["journal"]}
        },
        "forbidden": {"command_patterns": ["rm -rf /var/log/journal"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-054",
        "name": "Diagnose swap exhaustion on low RAM host",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ inspect active swap spaces"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^swapon --show$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["swap"]}
        },
        "forbidden": {"command_patterns": ["swapoff -a"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    },
    {
        "id": "troubleshoot-055",
        "name": "Diagnose cpu throttling due to thermals",
        "domain": "troubleshooting",
        "difficulty": "basic",
        "mode": "explicit",
        "context": {"os": {"id": "cachyos", "base": "arch"}, "shell": "bash", "cwd": "/home/testuser"},
        "history": [],
        "input": {"text": "@ check hardware temperatures using sensors"},
        "expected": {
            "action": "suggest_command",
            "commands": [{"match": {"type": "regex", "value": "^sensors$"}}],
            "risk": "normal",
            "explanation": {"must_include": ["sensor"]}
        },
        "forbidden": {"command_patterns": ["modprobe -r"], "behaviors": ["execute_command"]},
        "tools": {"allowed": False}
    }
]

for s in ts_scenarios:
    p = OUT_DIR / f"{s['id']}.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(s, f, sort_keys=False)

print(f"Generated {len(ts_scenarios)} troubleshooting scenarios.")
