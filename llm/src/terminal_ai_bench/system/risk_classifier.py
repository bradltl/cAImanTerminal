from __future__ import annotations

import re
from typing import Optional, Tuple

from .types import CommandAST


def classify_host_risk(ast: CommandAST) -> Tuple[str, Optional[str]]:
    """
    Deterministic host-owned risk classification.
    Overrides model hallucinations and sets authoritative risk & warning.
    Returns (risk_level, warning_message).
    """
    if not ast or not ast.raw_command:
        return "normal", None

    cmd = ast.raw_command.strip()
    exe = ast.executable or ""

    # 1. Elevated operations (sudo, disk formatting, system-wide mutations)
    if ast.has_sudo or exe == "sudo":
        # Check if read-only command wrapped in sudo
        if any(cmd.startswith(f"sudo {ro}") for ro in ("cat ", "head ", "tail ", "less ", "ss ", "du ", "journalctl ")):
            return "elevated", f"Elevated read privilege required for {exe}."
        return "elevated", f"Elevated system administrator operation executing with sudo privileges."

    elevated_patterns = [
        (r"\bmkfs(?:\.\w+)?\b", "Formats disk filesystem."),
        (r"\bdd\s+if=", "Low-level block device write with dd."),
        (r"\b(?:fdisk|gdisk|parted|wipefs)\b", "Partition table modification."),
        (r"\bpacman\s+-[a-zA-Z]*(?:R|S(?:y)?u)[a-zA-Z]*\b", "System-wide package installation or removal via pacman."),
        (r"\buser(?:del|add|mod)\b", "System user account modification."),
        (r"\bchmod\s+(?:-[a-zA-Z]*R[a-zA-Z]*\s+)?(?:777|a\+rwx)\b", "Permissive permission changes."),
        (r"\bsystemctl\s+(?:stop|restart|disable|mask|poweroff|reboot|reload)\b", "Controls systemd service state."),
        (r"\bchown\b", "Modifies system file ownership."),
        (r"\biptables\b", "Modifies network firewall filter rules."),
    ]
    for pat, warn in elevated_patterns:
        if re.search(pat, cmd):
            return "elevated", warn

    # 2. Caution operations (local state mutations, process termination, git updates)
    caution_patterns = [
        (r"\brm\b", "Deletes files or directories."),
        (r"\bgit\s+(?:checkout|reset|push|rebase|merge|clean|stash\s+drop|branch\s+-[dD]|restore)\b", "Git state mutation."),
        (r"\bgh\s+(?:pr\s+(?:merge|review)|release\s+delete|repo\s+delete|run\s+rerun|issue\s+close)\b", "Modifies remote GitHub state."),
        (r"\bgcloud\s+(?:config\s+set|compute\s+instances\s+(?:delete|stop|reset)|run\s+services\s+delete)\b", "GCP cloud resource modification."),
        (r"\baws\s+(?:ec2\s+(?:stop|terminate)-instances|s3\s+rm)\b", "AWS cloud resource modification."),
        (r"\baz\s+(?:vm\s+(?:stop|restart|delete))\b", "Azure resource modification."),
        (r"\b(?:kill|pkill|killall)\b", "Terminates running process."),
        (r"\bdocker\s+(?:rm|rmi|stop|compose\s+down|system\s+prune)\b", "Docker container or image removal."),
        (r"\bsed\s+-i\b", "Modifies file in-place."),
        (r"\bfallocate\b", "Allocates disk space."),
    ]
    for pat, warn in caution_patterns:
        if re.search(pat, cmd):
            return "caution", warn

    return "normal", None
