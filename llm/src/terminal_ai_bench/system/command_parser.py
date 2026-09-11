from __future__ import annotations

import re
import shlex
import subprocess
from typing import Dict, List, Optional, Tuple

from .types import CommandAST

# Known CLI tools that utilize hierarchical subcommand trees
SUBCOMMAND_TOOLS = {
    "gh": {"max_subcommands": 2},
    "gcloud": {"max_subcommands": 4},
    "git": {"max_subcommands": 2},
    "docker": {"max_subcommands": 2},
    "kubectl": {"max_subcommands": 2},
    "systemctl": {"max_subcommands": 1},
    "journalctl": {"max_subcommands": 0},
    "aws": {"max_subcommands": 2},
    "az": {"max_subcommands": 2},
    "pacman": {"max_subcommands": 0},
}


def check_shell_syntax(cmd: str) -> Tuple[bool, Optional[str]]:
    """Validate shell syntax using bash -n (read commands without executing)."""
    if not cmd or not cmd.strip():
        return False, "Empty command"
    try:
        res = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-n", "-c", cmd],
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if res.returncode != 0:
            err = res.stderr.strip() or "Syntax error in shell command"
            return False, err
        return True, None
    except Exception as e:
        return False, "Shell syntax check unavailable"  # Unknown is never syntax-valid.


def extract_command_substitutions(cmd: str) -> List[str]:
    """Find $(...) and backtick command substitutions."""
    subs = []
    # $(...) pattern
    for m in re.finditer(r"\$\(([^)]+)\)", cmd):
        subs.append(m.group(1).strip())
    # `...` pattern
    for m in re.finditer(r"`([^`]+)`", cmd):
        subs.append(m.group(1).strip())
    return subs


def parse_command(raw_cmd: str) -> CommandAST:
    """
    Parse a shell command into structured AST components without executing.
    Captures executable, subcommand hierarchy, flags, arguments, pipes, and safety signals.
    """
    cmd_str = raw_cmd.strip()
    if not cmd_str:
        return CommandAST(raw_command=raw_cmd, syntax_error="Empty command")

    is_syntax_valid, syntax_err = check_shell_syntax(cmd_str)
    substitutions = extract_command_substitutions(cmd_str)

    # Tokenize with punctuation support
    try:
        lexer = shlex.shlex(cmd_str, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except Exception as e:
        tokens = cmd_str.split()
        if not syntax_err:
            syntax_err = f"Lexing error: {e}"

    if not tokens:
        return CommandAST(raw_command=raw_cmd, syntax_error="No tokens parsed")

    # Detect pipes, logical operators, redirections
    pipelines: List[str] = []
    logical_ops: List[str] = []
    redirections: List[str] = []

    primary_tokens: List[str] = []
    idx = 0
    in_primary = True

    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("|", "|&"):
            pipelines.append(tok)
            in_primary = False
        elif tok in ("&&", "||", ";"):
            logical_ops.append(tok)
            in_primary = False
        elif tok in (">", ">>", "<", "<<", "&>", "2>", "2>&1", "1>&2"):
            redirections.append(tok)
            if idx + 1 < len(tokens):
                redirections.append(tokens[idx + 1])
                idx += 1
            in_primary = False
        else:
            if in_primary:
                primary_tokens.append(tok)
        idx += 1

    if not primary_tokens:
        primary_tokens = tokens

    # Unwrap sudo and environment setters
    has_sudo = False
    clean_tokens: List[str] = []
    t_idx = 0

    while t_idx < len(primary_tokens):
        tok = primary_tokens[t_idx]
        if tok == "sudo":
            has_sudo = True
            t_idx += 1
            # Skip sudo options like -u <user>, -E, -n
            while t_idx < len(primary_tokens):
                st = primary_tokens[t_idx]
                if st in ("-u", "-g") and t_idx + 1 < len(primary_tokens):
                    t_idx += 2
                elif st.startswith("-"):
                    t_idx += 1
                else:
                    break
            continue
        # Skip env vars like FOO=bar
        if "=" in tok and not tok.startswith("-") and not clean_tokens:
            t_idx += 1
            continue
        clean_tokens.append(tok)
        t_idx += 1

    if not clean_tokens:
        clean_tokens = primary_tokens

    executable = clean_tokens[0] if clean_tokens else None
    remaining = clean_tokens[1:]

    # Subcommands, flags, and arguments
    subcommands: List[str] = []
    arguments: List[str] = []
    flags: List[str] = []
    flag_map: Dict[str, Optional[str]] = {}
    filesystem_paths: List[str] = []

    max_sub = SUBCOMMAND_TOOLS.get(executable, {}).get("max_subcommands", 0) if executable else 0

    rem_idx = 0
    while rem_idx < len(remaining):
        token = remaining[rem_idx]

        if token.startswith("-"):
            flags.append(token)
            if "=" in token:
                f_name, f_val = token.split("=", 1)
                flag_map[f_name] = f_val
            else:
                # Flags that typically take a value
                takes_value_flags = {
                    "-u", "-o", "-i", "-t", "-m", "-c", "-n", "-k", "-p", "-s", "-e",
                    "--user", "--output", "--format", "--filter", "--region", "--zone",
                    "--project", "--name", "--title", "--body", "--label", "--tag", "--limit",
                    "--file", "--length", "--path", "--strategy"
                }
                is_numeric_flag = token[1:].isdigit() if len(token) > 1 else False
                if (
                    not is_numeric_flag
                    and token in takes_value_flags
                    and rem_idx + 1 < len(remaining)
                    and not remaining[rem_idx + 1].startswith("-")
                ):
                    flag_map[token] = remaining[rem_idx + 1]
                    rem_idx += 1
                else:
                    flag_map[token] = None
        else:
            # Check if this token could be a subcommand
            if len(subcommands) < max_sub and not flags:
                subcommands.append(token)
            else:
                arguments.append(token)
                # Check for filesystem paths
                if "/" in token or token in (".", "..", "~") or token.startswith("./") or token.startswith("../"):
                    filesystem_paths.append(token)

        rem_idx += 1

    return CommandAST(
        raw_command=raw_cmd,
        executable=executable,
        subcommands=subcommands,
        arguments=arguments,
        flags=flags,
        flag_map=flag_map,
        redirections=redirections,
        pipelines=pipelines,
        logical_operators=logical_ops,
        command_substitutions=substitutions,
        has_sudo=has_sudo,
        filesystem_paths=filesystem_paths,
        syntax_error=syntax_err,
    )
