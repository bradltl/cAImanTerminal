from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from .types import CommandAST, ValidationResult, ValidationStatus

# ── 1. GH CLI SPECIFICATIONS ──────────────────────────────────────────

GH_SUBCOMMANDS: Dict[str, Set[str]] = {
    "pr": {
        "checkout", "close", "comment", "create", "diff", "edit", "list",
        "merge", "ready", "reopen", "review", "status", "view"
    },
    "issue": {
        "close", "comment", "create", "delete", "develop", "edit", "list",
        "pin", "reopen", "status", "transfer", "unpin", "view"
    },
    "repo": {
        "archive", "clone", "create", "delete", "deploy-key", "edit",
        "fork", "list", "rename", "set-default", "sync", "view"
    },
    "run": {
        "cancel", "delete", "download", "list", "rerun", "view", "watch"
    },
    "release": {
        "create", "delete", "download", "edit", "list", "upload", "view"
    },
    "gist": {
        "clone", "create", "delete", "edit", "list", "view"
    },
    "auth": {
        "login", "logout", "refresh", "setup-git", "status", "switch", "token"
    },
    "label": {
        "clone", "create", "delete", "edit", "list"
    },
    "workflow": {
        "disable", "enable", "list", "run", "view"
    },
}

# ── 2. GCLOUD SPECIFICATIONS ──────────────────────────────────────────

GCLOUD_TREES: Dict[str, Dict[str, Set[str]]] = {
    "compute": {
        "instances": {"create", "delete", "describe", "list", "reset", "resume", "start", "stop", "suspend", "update", "add-tags", "remove-tags", "attach-disk", "detach-disk"},
        "addresses": {"create", "delete", "describe", "list"},
        "firewall-rules": {"create", "delete", "describe", "list", "update"},
        "disks": {"create", "delete", "describe", "list", "snapshot"},
        "networks": {"create", "delete", "describe", "list", "subnets"},
        "machine-types": {"list"},
        "ssh": set(),
    },
    "run": {
        "deploy": set(),
        "services": {"delete", "describe", "list", "replace", "update"},
        "revisions": {"delete", "describe", "list"},
    },
    "storage": {
        "ls": set(),
        "cp": set(),
        "rm": set(),
        "cat": set(),
        "buckets": {"create", "delete", "describe", "list"},
        "objects": {"list"},
    },
    "logging": {
        "read": set(),
        "write": set(),
        "logs": {"list", "delete"},
    },
    "auth": {
        "login": set(),
        "list": set(),
        "activate-service-account": set(),
        "print-access-token": set(),
        "revoke": set(),
    },
    "config": {
        "set": set(),
        "get": set(),
        "list": set(),
        "configurations": {"create", "delete", "describe", "list", "activate"},
    },
    "projects": {
        "list": set(),
        "describe": set(),
        "create": set(),
        "delete": set(),
        "get-iam-policy": set(),
        "add-iam-policy-binding": set(),
    },
    "sql": {
        "instances": {"describe", "list", "restart", "patch"},
    },
    "functions": {
        "deploy": set(),
        "describe": set(),
        "list": set(),
        "logs": set(),
        "call": set(),
    },
}

# ── 3. GIT SPECIFICATIONS ─────────────────────────────────────────────

GIT_SUBCOMMANDS: Set[str] = {
    "status", "diff", "log", "add", "commit", "push", "pull", "fetch",
    "checkout", "switch", "branch", "merge", "rebase", "stash", "tag",
    "clone", "init", "remote", "reset", "restore", "cherry-pick", "clean",
    "blame", "bisect", "config", "show", "reflog", "describe", "archive",
    "rev-parse", "rev-list", "ls-files", "ls-tree", "cat-file", "worktree",
    "submodule", "sparse-checkout", "rm", "mv"
}

# ── 4. SYSTEMCTL SPECIFICATIONS ───────────────────────────────────────

SYSTEMCTL_SUBCOMMANDS: Set[str] = {
    "start", "stop", "restart", "reload", "status", "enable", "disable",
    "mask", "unmask", "is-active", "is-enabled", "daemon-reload",
    "list-units", "list-unit-files", "cat", "edit", "reboot", "poweroff",
    "show", "reset-failed"
}

# ── 5. DOCKER SPECIFICATIONS ──────────────────────────────────────────

DOCKER_SUBCOMMANDS: Set[str] = {
    "run", "exec", "ps", "logs", "stop", "start", "restart", "rm", "rmi",
    "build", "pull", "push", "images", "inspect", "stats", "top", "network",
    "volume", "system", "compose", "cp", "login", "logout", "kill", "pause", "unpause"
}

DOCKER_COMPOSE_SUBCOMMANDS: Set[str] = {
    "up", "down", "build", "logs", "ps", "exec", "restart", "pull", "stop", "start", "config"
}

# ── CORE VALIDATOR IMPLEMENTATION ─────────────────────────────────────

def validate_gh(ast: CommandAST) -> ValidationResult:
    if not ast.subcommands:
        if ast.flags and any(f in ("-h", "--help", "--version") for f in ast.flags):
            return ValidationResult(status=ValidationStatus.VALID, executable="gh")
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="missing_subcommand",
            executable="gh",
            details="gh requires a top-level command like 'pr', 'issue', 'run', 'repo', 'release'.",
            help_topic="gh",
        )

    top = ast.subcommands[0]

    # Specific common LLM mistakes
    if top == "logs":
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gh",
            subcommand=["logs"],
            details="gh does not expose 'gh logs'. Use 'gh run view <run-id> --log'.",
            help_topic="gh run view",
            suggested_fix="gh run view <id> --log",
        )

    if top not in GH_SUBCOMMANDS:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gh",
            subcommand=[top],
            details=f"Unknown gh command '{top}'.",
            help_topic="gh",
        )

    if len(ast.subcommands) < 2:
        # Some commands allow leaf execution (like gh auth status or gh gist list)
        return ValidationResult(status=ValidationStatus.VALID, executable="gh", subcommand=[top])

    sub = ast.subcommands[1]
    valid_subs = GH_SUBCOMMANDS.get(top, set())

    # Check for 'gh pr approve' mistake
    if top == "pr" and sub == "approve":
        pr_id = ast.arguments[0] if ast.arguments else "<pr-id>"
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gh",
            subcommand=["pr", "approve"],
            details="Installed gh does not expose 'gh pr approve'. Use 'gh pr review <id> --approve'.",
            help_topic="gh pr review",
            suggested_fix=f"gh pr review {pr_id} --approve",
        )

    if sub not in valid_subs:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gh",
            subcommand=[top, sub],
            details=f"'{sub}' is not a valid '{top}' subcommand.",
            help_topic=f"gh {top}",
        )

    # Flag validation for gh pr merge
    if top == "pr" and sub == "merge":
        for f in ast.flags:
            if f.startswith("--strategy"):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="invalid_option",
                    executable="gh",
                    subcommand=["pr", "merge"],
                    details="gh pr merge does not take '--strategy'. Use '--rebase', '--squash', or '--merge'.",
                    help_topic="gh pr merge",
                    suggested_fix="gh pr merge <id> --rebase",
                )

    return ValidationResult(status=ValidationStatus.VALID, executable="gh", subcommand=[top, sub])


def validate_gcloud(ast: CommandAST) -> ValidationResult:
    if not ast.subcommands:
        return ValidationResult(status=ValidationStatus.VALID, executable="gcloud")

    group = ast.subcommands[0]
    if group not in GCLOUD_TREES:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gcloud",
            subcommand=[group],
            details=f"Unknown gcloud command group '{group}'.",
            help_topic="gcloud",
        )

    tree = GCLOUD_TREES[group]
    if len(ast.subcommands) < 2:
        return ValidationResult(status=ValidationStatus.VALID, executable="gcloud", subcommand=[group])

    sub = ast.subcommands[1]

    # Catch 'gcloud compute firewall' instead of 'firewall-rules'
    if group == "compute" and sub == "firewall":
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gcloud",
            subcommand=["compute", "firewall"],
            details="Unknown command 'firewall'. Use 'gcloud compute firewall-rules'.",
            help_topic="gcloud compute firewall-rules",
            suggested_fix="gcloud compute firewall-rules",
        )

    if sub not in tree:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="gcloud",
            subcommand=[group, sub],
            details=f"Unknown subcommand '{sub}' under 'gcloud {group}'.",
            help_topic=f"gcloud {group}",
        )

    leaf_set = tree[sub]
    if leaf_set and len(ast.subcommands) >= 3:
        action = ast.subcommands[2]
        if action not in leaf_set:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="unknown_subcommand",
                executable="gcloud",
                subcommand=[group, sub, action],
                details=f"Unknown action '{action}' for 'gcloud {group} {sub}'.",
                help_topic=f"gcloud {group} {sub}",
            )

    return ValidationResult(status=ValidationStatus.VALID, executable="gcloud", subcommand=ast.subcommands)


def validate_git(ast: CommandAST) -> ValidationResult:
    if not ast.subcommands:
        if ast.flags and any(f in ("-v", "--version", "--help") for f in ast.flags):
            return ValidationResult(status=ValidationStatus.VALID, executable="git")
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="missing_subcommand",
            executable="git",
            details="git requires a subcommand like 'status', 'log', 'commit', 'push'.",
            help_topic="git",
        )

    sub = ast.subcommands[0]
    if sub not in GIT_SUBCOMMANDS:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="git",
            subcommand=[sub],
            details=f"Unknown git subcommand '{sub}'.",
            help_topic="git",
        )

    return ValidationResult(status=ValidationStatus.VALID, executable="git", subcommand=[sub])


def validate_pacman(ast: CommandAST) -> ValidationResult:
    # Check for debian style 'pacman install' or 'pacman remove'
    if ast.arguments:
        first_arg = ast.arguments[0]
        if first_arg in ("install", "remove", "update", "upgrade", "search"):
            op_map = {"install": "-S", "remove": "-R", "update": "-Sy", "upgrade": "-Syu", "search": "-Ss"}
            op = op_map.get(first_arg, "-S")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="invalid_subcommand",
                executable="pacman",
                details=f"pacman does not have an '{first_arg}' subcommand. Use operation flag '{op}'.",
                help_topic="pacman",
                suggested_fix=f"sudo pacman {op} {' '.join(ast.arguments[1:])}",
            )

    # Validate operation flag
    has_valid_op = False
    for f in ast.flags:
        if re.match(r"^-[SQRFUDsqrfud]", f):
            has_valid_op = True
            break
    if not has_valid_op and not any(f in ("-h", "--help", "-V", "--version") for f in ast.flags):
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="invalid_option",
            executable="pacman",
            details="pacman requires a primary operation flag: -S (sync), -Q (query), -R (remove), -F (files), -U (upgrade).",
            help_topic="pacman",
        )

    return ValidationResult(status=ValidationStatus.VALID, executable="pacman")


def validate_systemctl(ast: CommandAST) -> ValidationResult:
    if not ast.subcommands:
        if ast.flags and any(f in ("--failed", "--version", "--help") for f in ast.flags):
            return ValidationResult(status=ValidationStatus.VALID, executable="systemctl")
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="missing_subcommand",
            executable="systemctl",
            details="systemctl requires a subcommand like 'start', 'stop', 'restart', 'status'.",
            help_topic="systemctl",
        )

    sub = ast.subcommands[0]
    if sub not in SYSTEMCTL_SUBCOMMANDS:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="systemctl",
            subcommand=[sub],
            details=f"Unknown systemctl command '{sub}'.",
            help_topic="systemctl",
        )

    return ValidationResult(status=ValidationStatus.VALID, executable="systemctl", subcommand=[sub])


def validate_docker(ast: CommandAST) -> ValidationResult:
    if not ast.subcommands:
        if ast.flags and any(f in ("-v", "--version", "--help") for f in ast.flags):
            return ValidationResult(status=ValidationStatus.VALID, executable="docker")
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="missing_subcommand",
            executable="docker",
            details="docker requires a subcommand like 'run', 'exec', 'ps', 'compose'.",
            help_topic="docker",
        )

    sub = ast.subcommands[0]
    if sub == "compose":
        if len(ast.subcommands) >= 2:
            c_sub = ast.subcommands[1]
            if c_sub not in DOCKER_COMPOSE_SUBCOMMANDS:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="unknown_subcommand",
                    executable="docker",
                    subcommand=["compose", c_sub],
                    details=f"Unknown docker compose subcommand '{c_sub}'.",
                    help_topic="docker compose",
                )
        return ValidationResult(status=ValidationStatus.VALID, executable="docker", subcommand=ast.subcommands)

    if sub not in DOCKER_SUBCOMMANDS:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="unknown_subcommand",
            executable="docker",
            subcommand=[sub],
            details=f"Unknown docker command '{sub}'.",
            help_topic="docker",
        )

    # Missing container for exec
    if sub == "exec" and not ast.arguments:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="missing_operand",
            executable="docker",
            subcommand=["exec"],
            details="docker exec requires a target container name or ID.",
            help_topic="docker exec",
        )

    return ValidationResult(status=ValidationStatus.VALID, executable="docker", subcommand=[sub])


def validate_coreutils(ast: CommandAST) -> ValidationResult:
    exe = ast.executable
    # Flag validation for grep
    if exe == "grep":
        for f in ast.flags:
            if f in ("--recursivee", "--recursiv"):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="invalid_option",
                    executable="grep",
                    details=f"Invalid option '{f}'. Use '-r' or '--recursive'.",
                    help_topic="grep",
                    suggested_fix=ast.raw_command.replace(f, "-r"),
                )

    if exe == "kill":
        if not ast.arguments and not ast.command_substitutions:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="kill",
                details="kill requires a PID operand.",
                help_topic="kill",
            )

    if exe == "fallocate":
        if not any(f in ("-l", "--length") for f in ast.flags) or not ast.arguments:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="fallocate",
                details="fallocate requires length option (-l <size>) and filename.",
                help_topic="fallocate",
            )

    return ValidationResult(status=ValidationStatus.VALID, executable=exe)


def validate_command(ast: CommandAST) -> ValidationResult:
    """
    Deterministic validator for candidate CLI commands.
    Returns VALID, INVALID, or UNKNOWN with structured diagnostics.
    """
    if ast.syntax_error:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="syntax_error",
            executable=ast.executable,
            details=ast.syntax_error,
        )

    exe = ast.executable
    if not exe:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="empty_command",
            details="Command has no executable.",
        )

    if exe == "gh":
        return validate_gh(ast)
    elif exe == "gcloud":
        return validate_gcloud(ast)
    elif exe == "git":
        return validate_git(ast)
    elif exe == "pacman":
        return validate_pacman(ast)
    elif exe in ("systemctl", "journalctl"):
        if exe == "systemctl":
            return validate_systemctl(ast)
        return ValidationResult(status=ValidationStatus.VALID, executable=exe)
    elif exe == "docker":
        return validate_docker(ast)
    elif exe in ("grep", "kill", "fallocate", "find", "cat", "ls", "tar", "sed", "awk", "diff", "ss", "df", "du", "pkill", "file", "sha256sum", "paccache", "reflector"):
        return validate_coreutils(ast)

    # For unknown utilities, return UNKNOWN (never guess)
    return ValidationResult(
        status=ValidationStatus.UNKNOWN,
        reason="untracked_executable",
        executable=exe,
        details=f"Executable '{exe}' is not in the deterministic validation catalog.",
    )
