from __future__ import annotations

import re
from typing import List, Optional

from .types import CommandAST, SafetyCheckResult, SafetyRuleViolation

CRITICAL_SYSTEM_DIRS = {"/", "/boot", "/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/sys", "/proc", "/dev", "/home"}
CRITICAL_PACKAGES = {"glibc", "linux", "systemd", "pacman", "bash", "coreutils"}


class SafetyValidator:
    """
    Deterministic Catastrophic Safety Gate for cAIman Terminal.
    Inspects commands statically and semantically to prevent catastrophic system damage.
    """

    def evaluate(self, ast: CommandAST) -> SafetyCheckResult:
        violations: List[SafetyRuleViolation] = []
        raw = ast.raw_command.strip()
        exe = ast.executable or ""
        paths = ast.filesystem_paths

        # 1. Pipe remote network content directly into shell/interpreter (curl | bash)
        if ast.pipelines and exe in ("curl", "wget", "fetch"):
            # Check if pipe targets an interpreter
            if any(p in raw for p in ("| bash", "| sh", "| zsh", "| python", "| perl", "| /bin/sh", "| /bin/bash")):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="remote_script_pipe_to_shell",
                        operation="pipe_to_shell",
                        target=exe,
                        severity="critical",
                        description="Piping remote network content directly into an executable shell.",
                    )
                )

        # 2. Fork bombs
        if re.search(r":\(\)\s*\{\s*:\|:&\s*\};:", raw) or re.search(r"\.\(\)\s*\{\s*\.\|\.&\s*\};", raw):
            violations.append(
                SafetyRuleViolation(
                    rule_name="fork_bomb",
                    operation="resource_exhaustion",
                    target="system",
                    severity="critical",
                    description="Malicious shell fork bomb detected.",
                )
            )

        # 3. Recursive deletion of critical paths
        is_rm = exe == "rm" or (exe == "sudo" and "rm" in ast.arguments)
        has_recursive_flag = any(
            f in ("-r", "-R", "-rf", "-fr", "-rfi", "-ri") or "--recursive" in f
            for f in ast.flags
        ) or any(
            arg in ("-r", "-R", "-rf", "-fr", "--recursive")
            for arg in ast.arguments
        )

        if is_rm and has_recursive_flag:
            targets = [p.rstrip("/") for p in paths]
            # Also check arguments for /
            for arg in ast.arguments:
                c = arg.strip("\"' ")
                if c in ("/", "/*", "/boot", "/boot/*", "/home", "/home/*", "/etc", "/etc/*", "/usr", "/usr/*"):
                    targets.append(c.rstrip("/*"))

            for t in targets:
                if t in ("/", ""):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_root_delete",
                            operation="recursive_delete",
                            target="/",
                            severity="critical",
                            description="Attempted recursive deletion of root filesystem.",
                        )
                    )
                elif t == "/boot":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_boot_delete",
                            operation="recursive_delete",
                            target="/boot",
                            severity="critical",
                            description="Attempted recursive deletion of boot partition /boot.",
                        )
                    )
                elif t == "/home":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_home_delete",
                            operation="recursive_delete",
                            target="/home",
                            severity="critical",
                            description="Attempted recursive deletion of all user home directories (/home).",
                        )
                    )
                elif t in ("/etc", "/usr", "/bin", "/lib"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_system_dir_delete",
                            operation="recursive_delete",
                            target=t,
                            severity="critical",
                            description=f"Attempted recursive deletion of critical system directory '{t}'.",
                        )
                    )

        # 4. Critical system file removal/moving (/etc/passwd, /etc/shadow)
        if exe in ("mv", "rm") or (exe == "sudo" and any(a in ("mv", "rm") for a in ast.arguments)):
            for p in paths:
                clean_p = p.strip("\"' ")
                if clean_p in ("/etc/passwd", "/etc/shadow", "/etc/sudoers"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="critical_system_file_tampering",
                            operation=f"{exe}_file",
                            target=clean_p,
                            severity="critical",
                            description=f"Attempted deletion or moving of critical credential database '{clean_p}'.",
                        )
                    )

        # 5. Dangerous recursive chmod 777 on system directories
        is_chmod = exe == "chmod" or (exe == "sudo" and "chmod" in ast.arguments)
        if is_chmod:
            has_777 = any(arg in ("777", "a+rwx", "ugo+rwx", "+rwx") for arg in ast.arguments + ast.flags)
            if has_777 or any("777" in f for f in ast.flags):
                for p in paths:
                    clean_p = p.strip("\"' ").rstrip("/")
                    if clean_p in ("/etc", "/usr", "/boot", "/bin", "/lib", "/", "/var"):
                        violations.append(
                            SafetyRuleViolation(
                                rule_name="dangerous_system_chmod",
                                operation="chmod_777",
                                target=clean_p,
                                severity="critical",
                                description=f"Dangerous permissive chmod 777 on critical system tree '{clean_p}'.",
                            )
                        )

        # 6. Dangerous recursive chown on system directories
        is_chown = exe == "chown" or (exe == "sudo" and "chown" in ast.arguments)
        if is_chown and has_recursive_flag:
            for p in paths:
                clean_p = p.strip("\"' ").rstrip("/")
                if clean_p in ("/usr", "/etc", "/boot", "/bin", "/lib", "/", "/var"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="dangerous_system_chown",
                            operation="recursive_chown",
                            target=clean_p,
                            severity="critical",
                            description=f"Recursive ownership alteration of critical system hierarchy '{clean_p}'.",
                        )
                    )

        # 7. Disk wiping via dd (targeting whole block device)
        if exe == "dd" or (exe == "sudo" and "dd" in ast.arguments):
            of_match = re.search(r"\bof=(/dev/(?:sd[a-z]|nvme\d+n\d+|vd[a-z]|hd[a-z]))\b", raw)
            if of_match:
                dev = of_match.group(1)
                violations.append(
                    SafetyRuleViolation(
                        rule_name="catastrophic_disk_wipe",
                        operation="dd_wipe",
                        target=dev,
                        severity="critical",
                        description=f"Direct raw block device wipe targeting '{dev}'.",
                    )
                )

        # 8. Partition table erasure / destruction
        if any(tool in raw for tool in ("wipefs -a", "sgdisk --zap-all", "sfdisk --delete")):
            violations.append(
                SafetyRuleViolation(
                    rule_name="partition_table_destruction",
                    operation="wipe_partition_table",
                    target="disk",
                    severity="critical",
                    description="Destructive clearing of storage disk partition tables.",
                )
            )

        # 9. Killing PID 1 (init / systemd)
        if exe in ("kill", "pkill") or (exe == "sudo" and any(a in ("kill", "pkill") for a in ast.arguments)):
            # Check for pid 1 as operand
            for arg in ast.arguments:
                if arg == "1":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="kill_init_pid_1",
                            operation="kill_process",
                            target="PID 1",
                            severity="critical",
                            description="Attempted termination of PID 1 (system init / systemd).",
                        )
                    )

        # 10. Critical package removal
        is_pkg_mgr = exe in ("pacman", "apt", "apt-get", "dnf", "yum", "zypper") or (
            exe == "sudo" and any(a in ("pacman", "apt", "apt-get", "dnf", "yum", "zypper") for a in ast.arguments)
        )
        if is_pkg_mgr:
            is_remove = any(
                any(rf in f for rf in ("-R", "remove", "purge", "erase"))
                for f in ast.flags + ast.arguments
            )
            if is_remove:
                for arg in ast.arguments:
                    if arg in CRITICAL_PACKAGES:
                        violations.append(
                            SafetyRuleViolation(
                                rule_name="critical_package_removal",
                                operation="package_remove",
                                target=arg,
                                severity="critical",
                                description=f"Attempted removal of foundational operating system package '{arg}'.",
                            )
                        )

        # 11. Insecure sudoers tampering
        if "/etc/sudoers" in raw and any(op in raw for op in (">>", ">", "tee -a", "tee")):
            if "NOPASSWD" in raw or "ALL=(ALL" in raw:
                violations.append(
                    SafetyRuleViolation(
                        rule_name="insecure_sudoers_tampering",
                        operation="sudoers_write",
                        target="/etc/sudoers",
                        severity="critical",
                        description="Insecure bypass of sudo authentication without visudo validation.",
                    )
                )

        if violations:
            critical_count = sum(1 for v in violations if v.severity == "critical")
            is_blocked = critical_count > 0
            desc = "; ".join(v.description for v in violations)
            return SafetyCheckResult(
                blocked=is_blocked,
                risk_level="blocked" if is_blocked else "elevated",
                violations=violations,
                warning=f"DETERMINISTIC SAFETY GATE BLOCKED: {desc}",
            )

        return SafetyCheckResult(blocked=False, risk_level="normal")
