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


# ── 6. TIER DEFINITIONS AND CATALOG SPECIFICATIONS ──────────────────

TIER_1_SPECIALIZED: Set[str] = {"gh", "gcloud", "git", "pacman", "systemctl", "docker"}

BASH_BUILTINS: Set[str] = {
    "echo", "printf", "cd", "pwd", "export", "unset", "source", "alias",
    "unalias", "type", "read", "exit", "return", "set", "shopt", "test",
    "[", "[[", "true", "false", "history", "help", "exec", "eval", "trap",
    ":", ".", "builtin", "command", "declare", "typeset", "local"
}

TIER_2_GENERIC: Set[str] = {
    "ls", "cp", "mv", "rm", "wc", "ln", "diff", "sort", "watch", "sha256sum",
    "pkill", "killall", "paccache", "ss", "lsof", "ip", "curl", "wget", "find",
    "cat", "grep", "fallocate", "kill", "tar", "sed", "awk", "df", "du", "file",
    "reflector", "mkinitcpio", "head", "tail", "touch", "chmod", "chown",
    "uname", "free", "ps", "uptime", "dmesg", "ping", "traceroute", "top",
    "htop", "tree", "hostname", "which", "whoami", "id", "env", "printenv",
    "tee", "cut", "tr", "uniq", "xargs", "gzip", "gunzip", "bzip2", "xz",
    "zip", "unzip", "ssh", "scp", "rsync", "journalctl", "netstat", "ncdu",
    "iostat", "vmstat", "iotop", "iptables", "ufw", "nft", "crontab", "locale",
    "localectl", "coredumpctl", "pip", "python", "python3", "openssl", "ssh-keygen",
    "mysql", "visudo", "swapoff", "lsmod"
}


def get_validator_tier(executable: Optional[str]) -> str:
    """Returns the catalog tier for an executable: 'specialized', 'generic', 'builtin', or 'unknown'."""
    if not executable:
        return "unknown"
    exe = executable.lower()
    if exe in TIER_1_SPECIALIZED:
        return "specialized"
    elif exe in BASH_BUILTINS:
        return "builtin"
    elif exe in TIER_2_GENERIC:
        return "generic"
    return "unknown"


def validate_bash_builtin(ast: CommandAST) -> ValidationResult:
    """Validates Bash builtin syntax and balance."""
    exe = ast.executable or ""
    if exe == "[":
        if not ast.arguments or ast.arguments[-1] != "]":
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="[",
                details="test '[' command missing closing ']'",
            )
    elif exe == "[[":
        if not ast.arguments or ast.arguments[-1] != "]]":
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="[[",
                details="test '[[' command missing closing ']]'",
            )
    return ValidationResult(status=ValidationStatus.VALID, executable=exe)


def validate_tier2_generic(ast: CommandAST) -> ValidationResult:
    """Tier 2 validator for generic Linux utilities with flag and argument checks."""
    exe = ast.executable or ""

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

    elif exe == "kill":
        if not ast.arguments and not ast.command_substitutions:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="kill",
                details="kill requires a PID operand.",
                help_topic="kill",
            )

    elif exe == "fallocate":
        if not any(f in ("-l", "--length") for f in ast.flags) or not ast.arguments:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="fallocate",
                details="fallocate requires length option (-l <size>) and filename.",
                help_topic="fallocate",
            )

    elif exe == "ln":
        if not ast.arguments:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="ln",
                details="ln requires target operand.",
                help_topic="ln",
            )

    elif exe == "pkill":
        if not ast.arguments and not any(f.startswith("-") for f in ast.flags):
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="pkill",
                details="pkill requires a pattern or process name operand.",
                help_topic="pkill",
            )

    elif exe == "watch":
        if not ast.arguments:
            return ValidationResult(
                status=ValidationStatus.INVALID,
                reason="missing_operand",
                executable="watch",
                details="watch requires a command to execute.",
                help_topic="watch",
            )

    elif exe == "sha256sum":
        for f in ast.flags:
            if f not in ("-c", "--check", "-b", "--binary", "-t", "--text", "--tag", "--quiet", "--status"):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="invalid_option",
                    executable="sha256sum",
                    details=f"Unknown option '{f}' for sha256sum.",
                    help_topic="sha256sum",
                )

    elif exe == "paccache":
        for f in ast.flags:
            valid_paccache = (
                bool(re.match(r"^-[rkuvcmdfq0-9]+$", f))
                or f in ("--remove", "--keep", "--uninstalled", "--clean", "--help", "--version")
            )
            if not valid_paccache:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="invalid_option",
                    executable="paccache",
                    details=f"Invalid option '{f}' for paccache.",
                    help_topic="paccache",
                )
    elif exe == "wc":
        for f in ast.flags:
            valid_wc = (
                bool(re.match(r"^-[cmlLw]+$", f))
                or f in ("--bytes", "--chars", "--lines", "--max-line-length", "--words", "--help", "--version")
                or f.startswith("--files0-from=")
            )
            if not valid_wc:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    reason="invalid_option",
                    executable="wc",
                    details=f"Invalid option '{f}' for wc.",
                    help_topic="wc",
                )

    return ValidationResult(status=ValidationStatus.VALID, executable=exe)


# Compatibility alias
validate_coreutils = validate_tier2_generic


def split_pipeline(cmd_str: str) -> List[str]:
    """Split shell pipeline by '|' outside quotes and subshells."""
    stages = []
    current: List[str] = []
    in_single = False
    in_double = False
    paren_depth = 0
    idx = 0
    while idx < len(cmd_str):
        c = cmd_str[idx]
        if c == "'" and not in_double:
            in_single = not in_single
            current.append(c)
        elif c == '"' and not in_single:
            in_double = not in_double
            current.append(c)
        elif c == '(' and not in_single:
            paren_depth += 1
            current.append(c)
        elif c == ')' and not in_single and paren_depth > 0:
            paren_depth -= 1
            current.append(c)
        elif c == '|' and not in_single and not in_double and paren_depth == 0:
            if idx + 1 < len(cmd_str) and cmd_str[idx + 1] in ('|', '&'):
                current.append(cmd_str[idx : idx + 2])
                idx += 1
            else:
                stages.append("".join(current).strip())
                current = []
        else:
            current.append(c)
        idx += 1
    if current:
        rem = "".join(current).strip()
        if rem:
            stages.append(rem)
    return stages if len(stages) > 1 else [cmd_str.strip()]


def _validate_single_command(ast: CommandAST) -> ValidationResult:
    """Validate a single command without pipeline splitting."""
    exe = ast.executable
    if not exe:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="empty_command",
            details="Command has no executable.",
        )

    tier = get_validator_tier(exe)
    if tier == "specialized":
        if exe == "gh":
            return validate_gh(ast)
        elif exe == "gcloud":
            return validate_gcloud(ast)
        elif exe == "git":
            return validate_git(ast)
        elif exe == "pacman":
            return validate_pacman(ast)
        elif exe == "systemctl":
            return validate_systemctl(ast)
        elif exe == "docker":
            return validate_docker(ast)
    elif tier == "builtin":
        return validate_bash_builtin(ast)
    elif tier == "generic":
        return validate_tier2_generic(ast)

    return ValidationResult(
        status=ValidationStatus.UNKNOWN,
        reason="untracked_executable",
        executable=exe,
        details=f"Executable '{exe}' is not in the deterministic validation catalog.",
    )


def validate_command(ast: CommandAST) -> ValidationResult:
    """
    Deterministic validator for candidate CLI commands.
    Supports Tier 1 (specialized), Tier 2 (generic), Bash builtins, multi-stage pipelines,
    and command substitutions.
    """
    if ast.syntax_error:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="syntax_error",
            executable=ast.executable,
            details=ast.syntax_error,
        )

    raw = ast.raw_command.strip()
    if not raw:
        return ValidationResult(
            status=ValidationStatus.INVALID,
            reason="empty_command",
            details="Command has no executable.",
        )

    # Multi-stage pipeline validation
    if ast.pipelines:
        from .command_parser import parse_command
        stages = split_pipeline(raw)
        if len(stages) > 1:
            has_unknown = False
            unknown_res = None
            for stage in stages:
                s_ast = parse_command(stage)
                s_res = _validate_single_command(s_ast)
                if s_res.status == ValidationStatus.INVALID:
                    return s_res
                if s_res.status == ValidationStatus.UNKNOWN:
                    has_unknown = True
                    if not unknown_res:
                        unknown_res = s_res
            if has_unknown and unknown_res:
                return unknown_res
            return ValidationResult(status=ValidationStatus.VALID, executable=ast.executable)

    # Command substitution validation
    if ast.command_substitutions:
        from .command_parser import parse_command
        for sub in ast.command_substitutions:
            sub_ast = parse_command(sub)
            sub_res = validate_command(sub_ast)
            if sub_res.status == ValidationStatus.INVALID:
                return sub_res

    return _validate_single_command(ast)
