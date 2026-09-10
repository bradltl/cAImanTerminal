from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .types import CommandAST, IntentContract, IntentStatus, IntentValidationResult


class IntentContractValidator:
    """
    Authoritative host-owned Intent Contract Validator.
    Deterministically evaluates whether a candidate command actually satisfies
    the semantic operation requested by the user, distinguishing between:
      1. Shell syntactic validity
      2. CLI structural legality (known subcommands/flags)
      3. Semantic task satisfaction (intent contract fulfilment)
    """

    def evaluate(self, ast: CommandAST, contract: Optional[IntentContract]) -> IntentValidationResult:
        if not contract or contract.domain == "unknown" or contract.operation == "unknown":
            return IntentValidationResult(
                status=IntentStatus.UNKNOWN,
                details="No deterministic contract evaluator exists for this operation.",
            )

        # Handle non-command operations (clarify, no_action)
        if contract.operation in ("clarify", "no_action"):
            if not ast or not ast.raw_command:
                return IntentValidationResult(
                    status=IntentStatus.SATISFIED,
                    domain=contract.domain,
                    operation=contract.operation,
                    details=f"Correctly produced non-command response for {contract.operation}.",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain=contract.domain,
                operation=contract.operation,
                details=f"Command '{ast.raw_command}' generated when task required {contract.operation}.",
            )

        if not ast or not ast.raw_command:
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain=contract.domain,
                operation=contract.operation,
                details="No command provided to evaluate against intent contract.",
            )

        domain = contract.domain.lower()
        if domain in ("pacman", "arch"):
            return self._evaluate_pacman(ast, contract)
        elif domain == "systemctl":
            return self._evaluate_systemctl(ast, contract)
        elif domain == "journalctl":
            return self._evaluate_journalctl(ast, contract)
        elif domain == "git":
            return self._evaluate_git(ast, contract)
        elif domain in ("gh", "github"):
            return self._evaluate_gh(ast, contract)
        elif domain in ("gcloud", "gcs"):
            return self._evaluate_gcloud(ast, contract)
        elif domain in ("filesystem", "bash", "coreutils"):
            return self._evaluate_filesystem(ast, contract)
        elif domain == "safety":
            return self._evaluate_safety(ast, contract)
        elif domain in ("troubleshoot", "troubleshooting"):
            return self._evaluate_troubleshoot(ast, contract)
        elif domain == "interaction":
            return self._evaluate_interaction(ast, contract)

        return IntentValidationResult(
            status=IntentStatus.UNKNOWN,
            domain=contract.domain,
            operation=contract.operation,
            details=f"Domain '{contract.domain}' does not have a dedicated intent contract evaluator.",
        )

    def _evaluate_pacman(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        params = contract.parameters
        exe = ast.executable or ""
        raw = ast.raw_command.strip()
        flags = set(ast.flags)
        args = ast.arguments

        if op == "clean_cache":
            # Expected: paccache -rk<N> or paccache -rk <N>
            is_paccache = exe == "paccache" or (exe == "sudo" and "paccache" in args)
            if is_paccache:
                retain_ver = str(params.get("retain_versions", "2"))
                has_k = any(
                    f.startswith(f"-k{retain_ver}")
                    or f"-rk{retain_ver}" in f
                    or f == "-k"
                    or retain_ver in args
                    for f in ast.flags + ast.arguments
                )
                if has_k or f"-k{retain_ver}" in raw or f"-k {retain_ver}" in raw or f"-rk{retain_ver}" in raw or f"-rk {retain_ver}" in raw:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="pacman",
                    operation=op,
                    details=f"Command runs paccache but does not specify retaining {retain_ver} versions (-k {retain_ver}).",
                    suggested_fix=f"sudo paccache -rk{retain_ver}",
                    help_topic="paccache",
                )
            elif exe == "pacman" and any("-S" in f and "c" in f for f in flags):
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="pacman",
                    operation=op,
                    details="Command cleans pacman cache with 'pacman -Sc', but does not retain specified previous versions (paccache).",
                    suggested_fix="sudo paccache -rk2",
                    help_topic="paccache",
                )
            elif exe == "pacman" and any("-R" in f for f in flags):
                return IntentValidationResult(
                    status=IntentStatus.MISMATCH,
                    domain="pacman",
                    operation=op,
                    details="Generated command removes packages ('pacman -R') instead of cleaning cached package files.",
                    suggested_fix="sudo paccache -rk2",
                    help_topic="paccache",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected cache cleaning command ('paccache -rk2'), got '{raw}'.",
                suggested_fix="sudo paccache -rk2",
                help_topic="paccache",
            )

        elif op == "downgrade_from_cache":
            is_u = (exe == "pacman" and any("-U" in f for f in flags)) or exe == "downgrade"
            if is_u:
                if "/var/cache/pacman/pkg" in raw or exe == "downgrade":
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="pacman",
                    operation=op,
                    details="Command invokes 'pacman -U', but does not target /var/cache/pacman/pkg archive.",
                )
            elif exe == "pacman" and any("-R" in f for f in flags):
                return IntentValidationResult(
                    status=IntentStatus.MISMATCH,
                    domain="pacman",
                    operation=op,
                    details="Generated command removes package ('pacman -R') instead of downgrading from local cache.",
                    suggested_fix="sudo pacman -U /var/cache/pacman/pkg/...",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected package downgrade from local cache ('pacman -U /var/cache/pacman/pkg/...'), got '{raw}'.",
            )

        elif op == "query_explicit":
            if exe == "pacman" and any("-Q" in f and "e" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            elif exe == "pacman" and any("-Q" in f for f in flags):
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="pacman",
                    operation=op,
                    details="Queries installed packages, but misses '-e' to restrict to explicitly installed packages.",
                    suggested_fix="pacman -Qe",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected explicit package query ('pacman -Qe'), got '{raw}'.",
            )

        elif op == "find_orphans":
            if exe == "pacman" and any("-Q" in f and "t" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected orphan query 'pacman -Qtdq', got '{raw}'.",
            )

        elif op == "package_owner":
            if exe == "pacman" and any("-Q" in f and "o" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected package owner lookup 'pacman -Qo <file>', got '{raw}'.",
            )

        elif op == "verify_package_files":
            if exe == "pacman" and any("-Q" in f and "k" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected package file verification 'pacman -Qk <pkg>', got '{raw}'.",
            )

        elif op == "upgrade_system":
            if exe == "pacman" and any("-S" in f and "u" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            elif exe == "pacman" and any("-S" in f and "y" in f for f in flags):
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="pacman",
                    operation=op,
                    details="Refreshes database (-Sy) but does not upgrade packages (-u).",
                    suggested_fix="sudo pacman -Syu",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="pacman",
                operation=op,
                details=f"Expected system upgrade 'pacman -Syu', got '{raw}'.",
            )

        elif op == "install":
            if exe == "pacman" and any("-S" in f and "u" not in f and "s" not in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected 'pacman -S <pkg>', got '{raw}'.")

        elif op == "remove":
            if exe == "pacman" and any("-R" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected 'pacman -R <pkg>', got '{raw}'.")

        elif op == "package_search":
            if exe == "pacman" and any(s in f for f in flags for s in ("-Ss", "-Qs", "-F")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected package search 'pacman -Ss <term>', got '{raw}'.")

        elif op == "query_installed":
            if exe == "pacman" and any("-Q" in f for f in flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected 'pacman -Q', got '{raw}'.")

        elif op == "mkinitcpio":
            if "mkinitcpio" in raw and any("-P" in f or "-p" in f for f in ast.flags + ast.arguments):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected 'sudo mkinitcpio -P', got '{raw}'.")

        elif op == "reflector":
            if "reflector" in raw and "mirrorlist" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected reflector mirrorlist update, got '{raw}'.")

        elif op == "lsmod":
            if exe == "lsmod":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="pacman", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="pacman", operation=op, details=f"Expected 'lsmod', got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="pacman", operation=op)

    def _evaluate_systemctl(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        params = contract.parameters
        service = params.get("service", "")
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if exe != "systemctl":
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="systemctl",
                operation=op,
                details=f"Expected systemctl command, got '{exe}'.",
            )

        if op == "enable_and_start":
            has_enable = "enable" in subcmds or "enable" in ast.arguments
            has_now = "--now" in ast.flags or any("--now" in a for a in ast.arguments)
            has_start = "start" in subcmds or "start" in ast.arguments

            if has_enable and has_now:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="systemctl", operation=op)
            elif has_enable and not has_now:
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="systemctl",
                    operation=op,
                    details=f"Command enables {service or 'service'} but does not start it. Missing '--now' flag.",
                    suggested_fix=f"sudo systemctl enable --now {service or '<service>'}",
                    help_topic="systemctl",
                )
            elif has_start and not has_enable:
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="systemctl",
                    operation=op,
                    details=f"Command starts {service or 'service'} but does not enable it on boot.",
                    suggested_fix=f"sudo systemctl enable --now {service or '<service>'}",
                    help_topic="systemctl",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="systemctl",
                operation=op,
                details=f"Expected 'systemctl enable --now {service or '<service>'}', got '{raw}'.",
            )

        elif op == "list_failed":
            if "--failed" in ast.flags or "failed" in ast.arguments or "failed" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="systemctl", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="systemctl",
                operation=op,
                details=f"Expected 'systemctl --failed', got '{raw}'.",
            )

        elif op in ("status", "start", "stop", "restart", "enable", "disable"):
            if op in subcmds or op in ast.arguments:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="systemctl", operation=op)
            actual_op = subcmds[0] if subcmds else "unknown"
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="systemctl",
                operation=op,
                details=f"Expected systemctl operation '{op}', got '{actual_op}'.",
            )

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="systemctl", operation=op)

    def _evaluate_journalctl(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        raw = ast.raw_command.strip()
        flags = set(ast.flags)

        if exe != "journalctl":
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="journalctl",
                operation=op,
                details=f"Expected journalctl command, got '{exe}'.",
            )

        if op == "kernel_logs":
            if "-k" in flags or "--dmesg" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="journalctl",
                operation=op,
                details="Expected kernel log inspection ('journalctl -k' or '--dmesg').",
                suggested_fix="journalctl -k",
            )

        elif op == "follow":
            if "-f" in flags or "--follow" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(
                status=IntentStatus.PARTIAL,
                domain="journalctl",
                operation=op,
                details="Command inspects journal logs but does not follow live output (-f).",
                suggested_fix="journalctl -f",
            )

        elif op == "previous_boot":
            if any("-b" in f and "-1" in raw for f in flags) or "--boot=-1" in raw or "-b -1" in raw or "-b-1" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            elif "-b" in flags or "--boot" in flags:
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="journalctl",
                    operation=op,
                    details="Inspects boot logs, but does not target previous boot (-b -1).",
                    suggested_fix="journalctl -b -1",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="journalctl",
                operation=op,
                details="Expected previous boot logs ('journalctl -b -1').",
            )

        elif op == "current_boot":
            if "-b" in flags or "--boot" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="journalctl",
                operation=op,
                details="Expected current boot log inspection ('journalctl -b').",
            )

        elif op == "unit_logs":
            if "-u" in flags or "--unit" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(status=IntentStatus.PARTIAL, domain="journalctl", operation=op, details="Missing unit filter flag '-u <unit>'.")

        elif op == "priority_filter":
            if "-p" in flags or "--priority" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(status=IntentStatus.PARTIAL, domain="journalctl", operation=op, details="Missing priority filter flag '-p <level>'.")

        elif op == "since_time":
            if "--since" in flags or "-S" in flags:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="journalctl", operation=op)
            return IntentValidationResult(status=IntentStatus.PARTIAL, domain="journalctl", operation=op, details="Missing time constraint flag '--since'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="journalctl", operation=op)

    def _evaluate_gh(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        params = contract.parameters
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if exe != "gh":
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="gh",
                operation=op,
                details=f"Expected 'gh' command, got '{exe}'.",
            )

        if op == "pr_review_approve":
            pr_num = str(params.get("pr_number", ""))
            # Catch invalid gh pr approve
            if "pr" in subcmds and ("approve" in subcmds or "approve" in ast.arguments):
                return IntentValidationResult(
                    status=IntentStatus.MISMATCH,
                    domain="gh",
                    operation=op,
                    details="gh CLI does not have a 'pr approve' subcommand. Must use 'gh pr review <number> --approve'.",
                    suggested_fix=f"gh pr review {pr_num or '<number>'} --approve",
                    help_topic="gh pr review",
                )
            if "pr" in subcmds and "review" in subcmds:
                has_approve = "--approve" in ast.flags or "-a" in ast.flags
                if has_approve:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="gh",
                    operation=op,
                    details="Command reviews PR but does not supply the '--approve' flag.",
                    suggested_fix=f"gh pr review {pr_num or '<number>'} --approve",
                    help_topic="gh pr review",
                )
            return IntentValidationResult(
                status=IntentStatus.MISMATCH,
                domain="gh",
                operation=op,
                details=f"Expected 'gh pr review {pr_num or '<number>'} --approve', got '{raw}'.",
            )

        elif op == "pr_merge":
            if "pr" in subcmds and "merge" in subcmds:
                strat = params.get("strategy")
                if strat == "rebase" and "--rebase" not in ast.flags:
                    return IntentValidationResult(
                        status=IntentStatus.PARTIAL,
                        domain="gh",
                        operation=op,
                        details="PR merge command missing requested rebase strategy flag '--rebase'.",
                        suggested_fix="gh pr merge <number> --rebase",
                        help_topic="gh pr merge",
                    )
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh pr merge', got '{raw}'.")

        elif op == "repo_fork":
            if "repo" in subcmds and "fork" in subcmds:
                if params.get("clone") and "--clone" not in ast.flags:
                    return IntentValidationResult(
                        status=IntentStatus.PARTIAL,
                        domain="gh",
                        operation=op,
                        details="Repository fork command missing '--clone' flag to clone locally.",
                        suggested_fix="gh repo fork <repo> --clone",
                    )
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh repo fork', got '{raw}'.")

        elif op == "workflow_run_logs":
            if "run" in subcmds and "view" in subcmds:
                if any(f in ("--log", "--log-failed") for f in ast.flags):
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="gh",
                    operation=op,
                    details="Views workflow run but misses '--log' or '--log-failed' to display run logs.",
                    suggested_fix="gh run view <id> --log",
                    help_topic="gh run view",
                )
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh run view <id> --log', got '{raw}'.")

        elif op == "release_create":
            if "release" in subcmds and "create" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh release create', got '{raw}'.")

        elif op == "issue_create":
            if "issue" in subcmds and "create" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh issue create', got '{raw}'.")

        elif op == "issue_close":
            if "issue" in subcmds and "close" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh issue close', got '{raw}'.")

        elif op == "issue_list":
            if "issue" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh issue list', got '{raw}'.")

        elif op == "pr_list":
            if "pr" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh pr list', got '{raw}'.")

        elif op == "pr_diff":
            if "pr" in subcmds and "diff" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh pr diff', got '{raw}'.")

        elif op == "repo_clone":
            if "repo" in subcmds and "clone" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh repo clone', got '{raw}'.")

        elif op == "gist_list":
            if "gist" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh gist list', got '{raw}'.")

        elif op == "label_list":
            if "label" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gh", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gh", operation=op, details=f"Expected 'gh label list', got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="gh", operation=op)

    def _evaluate_filesystem(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        params = contract.parameters
        exe = ast.executable or ""
        raw = ast.raw_command.strip()

        if op == "create_symlink":
            if exe == "ln" and any("-s" in f for f in ast.flags):
                source = params.get("source")
                destination = params.get("destination")
                import shlex
                try:
                    tokens = [t for t in shlex.split(raw) if not t.startswith("-") and t not in ("ln", "sudo")]
                except Exception:
                    tokens = [a for a in ast.arguments if not a.startswith("-")]
                if source and destination and len(tokens) >= 2:
                    actual_src, actual_dst = tokens[0], tokens[1]
                    if source in actual_dst and destination in actual_src:
                        return IntentValidationResult(
                            status=IntentStatus.MISMATCH,
                            domain="filesystem",
                            operation=op,
                            details=f"Symlink source and destination arguments are inverted: got 'ln -s {actual_src} {actual_dst}', expected 'ln -s {source} {destination}'.",
                            suggested_fix=f"ln -s {source} {destination}",
                        )
                    if source in actual_src and destination in actual_dst:
                        return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            elif exe == "ln":
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="filesystem",
                    operation=op,
                    details="Creates hard link instead of symbolic link (missing '-s').",
                    suggested_fix="ln -s <source> <destination>",
                )
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'ln -s', got '{raw}'.")

        elif op == "checksum":
            mode = params.get("mode", "compute")
            is_cksum = any(h in exe for h in ("sha256sum", "sha1sum", "md5sum", "b2sum", "sha512sum"))
            has_c = any("-c" in f or "--check" in f for f in ast.flags)

            if not is_cksum:
                return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected checksum utility, got '{exe}'.")

            if mode == "verify":
                if has_c:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.MISMATCH,
                    domain="filesystem",
                    operation=op,
                    details="Generated command computes checksum instead of verifying manifest with '-c'.",
                    suggested_fix="sha256sum -c <checksum_file>",
                )
            elif mode == "compute":
                if has_c:
                    return IntentValidationResult(
                        status=IntentStatus.MISMATCH,
                        domain="filesystem",
                        operation=op,
                        details="Generated command verifies checksum with '-c' instead of computing file checksum.",
                        suggested_fix="sha256sum <file>",
                    )
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)

        elif op == "download_file":
            if exe == "curl":
                has_out = any("-o" in f or "-O" in f or "--output" in f for f in ast.flags + ast.arguments)
                if has_out:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
                return IntentValidationResult(
                    status=IntentStatus.PARTIAL,
                    domain="filesystem",
                    operation=op,
                    details="curl command outputs to stdout instead of saving to destination file (-o <dest>).",
                    suggested_fix="curl -L -o <dest> <url>",
                )
            elif exe == "wget":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected curl or wget download, got '{raw}'.")

        elif op == "compare_files":
            if exe in ("diff", "cmp", "git") or "diff" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected file comparison ('diff'), got '{raw}'.")

        elif op == "list_listening_ports":
            is_socket = any(s in raw for s in ("ss -tul", "ss -tlpn", "ss -tulpn", "netstat -tul", "lsof -i"))
            if is_socket:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected listening ports command ('ss -tulpn' or 'lsof -i'), got '{raw}'.")

        elif op == "preallocate_file":
            if exe == "fallocate" and any("-l" in f for f in ast.flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'fallocate -l <size> <path>', got '{raw}'.")

        elif op == "count_lines":
            if exe == "wc" and any("-l" in f for f in ast.flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'wc -l <file>', got '{raw}'.")

        elif op == "sort_csv_column":
            if exe == "sort" and any("-t" in f for f in ast.flags + ast.arguments):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'sort -t, -k... <file>', got '{raw}'.")

        elif op == "text_replace":
            if exe == "sed" and any("-i" in f for f in ast.flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'sed -i ...', got '{raw}'.")

        elif op == "create_tarball":
            if exe == "tar" and any(c in raw for c in ("-c", "-czf", "-czvf", "czf", "czvf")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'tar -czf ...', got '{raw}'.")

        elif op == "disk_usage":
            if exe in ("du", "df"):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'du -sh' or 'df -h', got '{raw}'.")

        elif op == "watch_command":
            if exe == "watch":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'watch -n ...', got '{raw}'.")

        elif op == "kill_process_by_name":
            if exe in ("pkill", "killall"):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'pkill <name>' or 'killall <name>', got '{raw}'.")

        elif op == "identify_file_type":
            if exe == "file":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'file <target>', got '{raw}'.")

        elif op == "print_env_var":
            if exe in ("echo", "printenv") or (exe == "env" and "PATH" in raw):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="filesystem", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="filesystem", operation=op, details=f"Expected 'echo $PATH' or 'printenv PATH', got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="filesystem", operation=op)

    def _evaluate_gcloud(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if exe not in ("gcloud", "gsutil"):
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected gcloud or gsutil, got '{exe}'.")

        if op == "set_project":
            if "config" in subcmds and "set" in subcmds and ("project" in ast.arguments or "project" in subcmds):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud config set project', got '{raw}'.")

        elif op == "set_region":
            if "config" in subcmds and "set" in subcmds and ("compute/region" in raw or any("region" in a for a in ast.arguments + subcmds)):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud config set compute/region', got '{raw}'.")

        elif op == "list_instances":
            if "compute" in subcmds and "instances" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud compute instances list', got '{raw}'.")

        elif op == "stop_instance":
            if "compute" in subcmds and "instances" in subcmds and "stop" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud compute instances stop', got '{raw}'.")

        elif op == "list_addresses":
            if "compute" in subcmds and "addresses" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud compute addresses list', got '{raw}'.")

        elif op == "list_machine_types":
            if "compute" in subcmds and "machine-types" in subcmds and "list" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud compute machine-types list', got '{raw}'.")

        elif op == "storage_copy":
            if ("storage" in subcmds or exe == "gsutil") and ("cp" in subcmds or "cp" in ast.arguments or "cp" in raw):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud storage cp' or 'gsutil cp', got '{raw}'.")

        elif op == "storage_list":
            if ("storage" in subcmds or exe == "gsutil") and ("ls" in subcmds or "list" in subcmds or "ls" in ast.arguments or "ls" in raw):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud storage ls' or 'gsutil ls', got '{raw}'.")

        elif op == "sql_describe":
            if "sql" in subcmds and "instances" in subcmds and "describe" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud sql instances describe', got '{raw}'.")

        elif op == "function_logs":
            if "functions" in subcmds and "logs" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud functions logs read', got '{raw}'.")

        elif op == "cloud_run_logs":
            if ("run" in subcmds and "logs" in subcmds) or ("logging" in subcmds and "read" in subcmds):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud run services logs read', got '{raw}'.")

        elif op == "cloud_run_deploy":
            if "run" in subcmds and "deploy" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud run deploy', got '{raw}'.")

        elif op == "iam_policy":
            if "get-iam-policy" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud ... get-iam-policy', got '{raw}'.")

        elif op == "create_firewall_rule":
            if "compute" in subcmds and "firewall-rules" in subcmds and "create" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="gcloud", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="gcloud", operation=op, details=f"Expected 'gcloud compute firewall-rules create ...', got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="gcloud", operation=op)

    def _evaluate_git(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if exe != "git":
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected git command, got '{exe}'.")

        if op == "create_branch":
            if ("checkout" in subcmds and "-b" in ast.flags) or ("switch" in subcmds and "-c" in ast.flags) or ("branch" in subcmds):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected branch creation ('git checkout -b' or 'git switch -c'), got '{raw}'.")

        elif op == "pull_rebase":
            if "pull" in subcmds:
                if "--rebase" in ast.flags or "-r" in ast.flags:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
                return IntentValidationResult(status=IntentStatus.PARTIAL, domain="git", operation=op, details="Runs 'git pull' but misses '--rebase' flag.", suggested_fix="git pull --rebase")
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git pull --rebase', got '{raw}'.")

        elif op == "push_set_upstream":
            if "push" in subcmds:
                if "-u" in ast.flags or "--set-upstream" in ast.flags:
                    return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
                return IntentValidationResult(status=IntentStatus.PARTIAL, domain="git", operation=op, details="Runs 'git push' but misses upstream tracking flag ('-u' or '--set-upstream').", suggested_fix="git push -u origin <branch>")
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git push -u origin <branch>', got '{raw}'.")

        elif op == "stash":
            if "stash" in subcmds and "pop" not in subcmds and "drop" not in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git stash', got '{raw}'.")

        elif op == "stash_pop":
            if "stash" in subcmds and ("pop" in subcmds or "pop" in ast.arguments):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git stash pop', got '{raw}'.")

        elif op == "show_conflicts":
            if ("diff" in subcmds and "--diff-filter=U" in raw) or "status" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected merge conflicts check, got '{raw}'.")

        elif op == "status":
            if "status" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git status', got '{raw}'.")

        elif op == "diff":
            if "diff" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git diff', got '{raw}'.")

        elif op == "pull":
            if "pull" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git pull', got '{raw}'.")

        elif op == "push":
            if "push" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git push', got '{raw}'.")

        elif op == "merge":
            if "merge" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="git", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="git", operation=op, details=f"Expected 'git merge', got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="git", operation=op)

    def _evaluate_safety(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        raw = ast.raw_command.strip()

        if op == "safe_disk_formatting":
            if "mkfs" in exe or "mkfs" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected safe format command ('sudo mkfs.ext4 /dev/...'), got '{raw}'.")

        elif op == "journal_vacuum":
            if exe == "journalctl" and any("--vacuum" in f for f in ast.flags + ast.arguments):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected journal vacuum ('journalctl --vacuum-time=...'), got '{raw}'.")

        elif op == "safe_mysql_password":
            if exe == "mysql" and any("-p" in f for f in ast.flags):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected safe MySQL prompt flag ('mysql -u root -p'), got '{raw}'.")

        elif op == "safe_visudo":
            if "visudo" in exe or "visudo" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected safe sudoers edit ('sudo visudo'), got '{raw}'.")

        elif op == "safe_swapoff":
            if "swapoff" in exe or "swapoff" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected swap disabling ('sudo swapoff -a'), got '{raw}'.")

        elif op == "safe_ssh_keygen":
            if "ssh-keygen" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="safety", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="safety", operation=op, details=f"Expected keygen ('ssh-keygen'), got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="safety", operation=op)

    def _evaluate_troubleshoot(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if op == "diagnose_network":
            if any(n in exe for n in ("ip", "traceroute", "ping", "tracepath")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected network diagnosis command ('ip route', 'ping', 'traceroute'), got '{raw}'.")

        elif op == "missing_shared_lib":
            if "pacman -F" in raw or "pkgfile" in raw or "pacman -Ss" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected shared library lookup ('pacman -F <lib>'), got '{raw}'.")

        elif op == "disk_space_exhaustion":
            if exe == "df":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected disk check ('df -h'), got '{raw}'.")

        elif op == "port_collision":
            if any(s in raw for s in ("ss -tul", "ss -tlpn", "ss -tulpn", "lsof -i")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected port diagnosis ('ss -tulpn' or 'lsof -i :port'), got '{raw}'.")

        elif op == "high_cpu_load":
            if any(c in exe for c in ("top", "htop", "ps")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected CPU diagnosis ('top', 'htop', 'ps aux --sort=-%cpu'), got '{raw}'.")

        elif op == "find_broken_symlinks":
            if exe == "find" and "-xtype" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected 'find . -xtype l', got '{raw}'.")

        elif op == "dns_resolution_failure":
            if any(d in exe for d in ("resolvectl", "cat", "dig", "ping", "nslookup", "systemd-resolve")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected DNS diagnostic ('resolvectl status', 'cat /etc/resolv.conf'), got '{raw}'.")

        elif op == "docker_socket_permissions":
            if "usermod" in raw or ("docker" in raw and "chmod" not in raw):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected safe docker permission fix ('sudo usermod -aG docker $USER'), got '{raw}'.")

        elif op == "diagnose_oom":
            if any(e in exe for e in ("free", "cat", "dmesg", "swapon")) or "meminfo" in raw or "oom" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected OOM diagnostic ('free -m', 'dmesg | grep -i oom'), got '{raw}'.")

        elif op == "diagnose_disk_usage":
            if exe in ("du", "df"):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected 'du -sh /tmp', got '{raw}'.")

        elif op == "diagnose_ssh_service":
            if any(s in raw for s in ("ss", "systemctl", "nc", "ssh")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected SSH diagnosis ('systemctl status sshd' or 'ss -tlnp'), got '{raw}'.")

        elif op == "diagnose_package_dep":
            if any(p in exe for p in ("pacman", "pactree", "yay")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected package dependency check ('pacman -Qi' or 'pactree'), got '{raw}'.")

        elif op == "diagnose_io":
            if any(i in exe for i in ("iostat", "iotop", "dstat", "vmstat")) or "diskstats" in raw:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected IO diagnostic ('iostat', 'iotop', 'vmstat'), got '{raw}'.")

        elif op == "diagnose_firewall":
            if any(f in exe for f in ("iptables", "nft", "firewall-cmd", "ss", "ufw")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected firewall check ('iptables -L -n', 'firewall-cmd --list-all'), got '{raw}'.")

        elif op == "diagnose_segfault":
            if any(s in exe for s in ("coredumpctl", "gdb", "dmesg")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected segfault diagnosis ('coredumpctl info', 'dmesg | grep segfault'), got '{raw}'.")

        elif op == "diagnose_missing_python_module":
            if exe in ("pip", "pip3") and "install" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected module installation ('pip install <package>'), got '{raw}'.")

        elif op == "diagnose_locale":
            if exe == "file":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected file encoding check ('file -i <file>'), got '{raw}'.")

        elif op == "diagnose_cron":
            if any(c in exe for c in ("crontab", "journalctl", "grep", "systemctl")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected cron diagnosis ('crontab -l', 'journalctl -u cronie'), got '{raw}'.")

        elif op == "diagnose_io_wait":
            if any(i in exe for i in ("iostat", "vmstat", "iotop", "pidstat")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected IO wait diagnostic ('iostat -x', 'vmstat'), got '{raw}'.")

        elif op == "diagnose_zombie_process":
            if exe == "ps" and any(w in raw for w in ("grep", "awk", "Z", "defunct")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="troubleshoot", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="troubleshoot", operation=op, details=f"Expected zombie process check ('ps aux | grep Z'), got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="troubleshoot", operation=op)

    def _evaluate_interaction(self, ast: CommandAST, contract: IntentContract) -> IntentValidationResult:
        op = contract.operation
        exe = ast.executable or ""
        subcmds = ast.subcommands
        raw = ast.raw_command.strip()

        if op == "typo_kubectl":
            if exe == "kubectl":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'kubectl ...', got '{raw}'.")

        elif op == "typo_git":
            if exe == "git" and "status" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'git status', got '{raw}'.")

        elif op == "typo_docker":
            if exe == "docker" and "compose" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'docker compose ...', got '{raw}'.")

        elif op == "ghost_completion_docker":
            if exe == "docker" and "exec" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'docker exec ...', got '{raw}'.")

        elif op == "ghost_completion_pacman":
            if "pacman" in raw and any(f in raw for f in ("-S", "install")):
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'sudo pacman -S ...', got '{raw}'.")

        elif op == "context_python_traceback":
            if exe in ("pip", "pip3") and "install" in subcmds:
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected 'pip install ...', got '{raw}'.")

        elif op == "multi_turn_git_branch":
            if exe == "git":
                return IntentValidationResult(status=IntentStatus.SATISFIED, domain="interaction", operation=op)
            return IntentValidationResult(status=IntentStatus.MISMATCH, domain="interaction", operation=op, details=f"Expected git branch/push command, got '{raw}'.")

        return IntentValidationResult(status=IntentStatus.UNKNOWN, domain="interaction", operation=op)
