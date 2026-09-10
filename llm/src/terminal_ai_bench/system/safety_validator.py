from __future__ import annotations

import re
import shlex
from typing import List, Optional, Set, Tuple

from .types import CommandAST, IntentContract, SafetyCheckResult, SafetyRuleViolation

# Comprehensive regex for Linux block devices (whole disks and partitions)
BLOCK_DEVICE_PATTERN = re.compile(
    r"^/dev/(?:"
    r"sd[a-z][0-9]*|"                      # SCSI/SATA disks & partitions: /dev/sda, /dev/sdb1
    r"nvme\d+n\d+(?:p\d+)?|"               # NVMe namespaces & partitions: /dev/nvme0n1, /dev/nvme0n1p2
    r"mmcblk\d+(?:p\d+)?|"                 # MMC/SD cards & partitions: /dev/mmcblk0, /dev/mmcblk0p1
    r"vd[a-z][0-9]*|"                      # VirtIO virtual disks & partitions: /dev/vda, /dev/vdb1
    r"xvd[a-z][0-9]*|"                     # Xen virtual disks: /dev/xvda, /dev/xvdf1
    r"hd[a-z][0-9]*|"                      # IDE legacy disks & partitions: /dev/hda, /dev/hdb1
    r"mapper/[^/\s]+|"                     # Device mapper / LVM / LUKS: /dev/mapper/root, /dev/mapper/vg-lv
    r"loop\d+(?:p\d+)?|"                   # Loopback devices: /dev/loop0, /dev/loop0p1
    r"md\d+(?:p\d+)?|"                     # Linux Software RAID: /dev/md0, /dev/md127p1
    r"dm-\d+|"                             # Device mapper numeric: /dev/dm-0
    r"disk/by-[a-z-]+/[^/\s]+"             # Persistent device symlinks: /dev/disk/by-id/..., /dev/disk/by-uuid/...
    r")$"
)

# Whole primary disks (root or entire disk without partition number)
WHOLE_DISK_PATTERN = re.compile(
    r"^/dev/(?:"
    r"sd[a-z]|"
    r"nvme\d+n\d+|"
    r"mmcblk\d+|"
    r"vd[a-z]|"
    r"xvd[a-z]|"
    r"hd[a-z]"
    r")$"
)

CRITICAL_SYSTEM_DIRS = {
    "/", "/boot", "/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64",
    "/sys", "/proc", "/dev", "/home"
}
CRITICAL_SYSTEM_FILES = {"/etc/passwd", "/etc/shadow", "/etc/sudoers", "/etc/pacman.conf"}
CRITICAL_PACKAGES = {
    "glibc", "systemd", "linux", "linux-firmware", "bash", "pacman", "filesystem", "coreutils", "sudo"
}


def is_block_device_target(path: str) -> bool:
    """Determine if a path points to a real or virtual Linux block device."""
    if not path:
        return False
    clean = path.strip("\"' ").rstrip("/")
    return bool(BLOCK_DEVICE_PATTERN.match(clean))


def is_whole_disk_target(path: str) -> bool:
    """Determine if a path points to a whole disk rather than an individual partition."""
    if not path:
        return False
    clean = path.strip("\"' ").rstrip("/")
    return bool(WHOLE_DISK_PATTERN.match(clean))


def find_block_device_targets(raw_cmd: str, ast: Optional[CommandAST] = None) -> List[str]:
    """Find all block devices mentioned as arguments, paths, redirections, or raw matches."""
    found: Set[str] = set()
    if ast:
        for p in ast.filesystem_paths + ast.arguments + ast.redirections:
            clean = p.strip("\"' ").rstrip("/")
            if is_block_device_target(clean):
                found.add(clean)
    for m in re.finditer(r"/dev/(?:[a-zA-Z0-9_\-/\.]+)", raw_cmd):
        cand = m.group(0).rstrip(";,)\"'")
        if is_block_device_target(cand):
            found.add(cand)
    return sorted(list(found))


def intent_allows_formatting(contract: Optional[IntentContract], user_intent: Optional[str]) -> bool:
    if contract:
        op = contract.operation.lower()
        if any(w in op for w in ("format", "mkfs", "filesystem")):
            return True
    if user_intent:
        norm = user_intent.lower()
        if any(w in norm for w in ("format ", "formatting", "mkfs", "create filesystem", "make filesystem")):
            return True
    return False


def intent_allows_raw_disk_write(contract: Optional[IntentContract], user_intent: Optional[str]) -> bool:
    if contract:
        op = contract.operation.lower()
        if any(w in op for w in ("raw_disk_write", "flash_iso", "burn_image", "write_image")):
            return True
    if user_intent:
        norm = user_intent.lower()
        if any(w in norm for w in ("flash iso", "write image", "burn image", "dd to", "dd image", "raw write")):
            return True
    return False


def intent_allows_partition_destruction(contract: Optional[IntentContract], user_intent: Optional[str]) -> bool:
    if contract:
        op = contract.operation.lower()
        if any(w in op for w in ("partition", "wipefs", "sgdisk", "fdisk", "parted")):
            return True
    if user_intent:
        norm = user_intent.lower()
        if any(w in norm for w in ("partition", "wipefs", "zap-all", "clear partition", "delete partition")):
            return True
    return False


def intent_allows_firewall_mutation(contract: Optional[IntentContract], user_intent: Optional[str]) -> bool:
    if contract:
        op = contract.operation.lower()
        if any(w in op for w in ("firewall_flush", "flush_firewall", "disable_firewall", "reset_firewall")):
            return True
    if user_intent:
        norm = user_intent.lower()
        if any(w in norm for w in ("flush firewall", "disable firewall", "flush rules", "clear firewall", "turn off firewall", "reset ufw")):
            return True
    return False


def intent_allows_file_deletion(contract: Optional[IntentContract], user_intent: Optional[str]) -> bool:
    if contract:
        op = contract.operation.lower()
        if any(w in op for w in ("delete", "remove", "clean", "purge", "erase", "vacuum")) or contract.destructive:
            return True
    if user_intent:
        norm = user_intent.lower()
        if any(w in norm for w in ("delete", "remove", "clean", "purge", "erase", "vacuum", "free up space")):
            return True
    return False


class SafetyValidator:
    """
    Authoritative Deterministic Safety Gate for cAIman Terminal.
    Inspects commands statically and semantically to prevent catastrophic system damage.
    Defends against model mistakes even when:
      - executable is untracked
      - generated command is semantically unrelated to user request
      - model risk classification is wrong
      - benchmark does not contain an exact regex match
    """

    def evaluate(
        self,
        ast: CommandAST,
        intent_contract: Optional[IntentContract] = None,
        user_intent: Optional[str] = None,
    ) -> SafetyCheckResult:
        violations: List[SafetyRuleViolation] = []
        raw = ast.raw_command.strip()
        exe = ast.executable or ""
        paths = ast.filesystem_paths

        # Determine effective executable if wrapped in sudo
        effective_exe = exe
        effective_args = list(ast.arguments)
        effective_flags = list(ast.flags)
        if (exe == "sudo" or ast.has_sudo) and ast.arguments:
            if exe == "sudo":
                for idx, a in enumerate(ast.arguments):
                    if not a.startswith("-"):
                        effective_exe = a
                        effective_args = ast.arguments[idx + 1 :]
                        break

        # 1. Pipe remote network content directly into shell/interpreter (curl | bash)
        if ast.pipelines and effective_exe in ("curl", "wget", "fetch"):
            if any(p in raw for p in ("| bash", "| sh", "| zsh", "| python", "| perl", "| /bin/sh", "| /bin/bash")):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="remote_script_pipe_to_shell",
                        operation="pipe_to_shell",
                        target=effective_exe,
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

        # 3. Filesystem formatting detection (mkfs, mkfs.*, mke2fs, newfs)
        is_format_cmd = (
            effective_exe == "mkfs"
            or effective_exe.startswith("mkfs.")
            or effective_exe in ("mke2fs", "newfs")
            or bool(re.search(r"\b(?:sudo\s+)?(mkfs(?:\.[a-zA-Z0-9_\-]+)?|mke2fs|newfs)\b", raw))
        )
        if is_format_cmd:
            dev_targets = find_block_device_targets(raw, ast)
            primary_target = dev_targets[0] if dev_targets else (effective_args[0] if effective_args else "device")
            if not intent_allows_formatting(intent_contract, user_intent):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="unexpected_filesystem_format",
                        operation="mkfs",
                        target=primary_target,
                        severity="critical",
                        description=f"Filesystem format command '{effective_exe}' targeting '{primary_target}' generated without format request in user intent.",
                    )
                )
            else:
                # Formatting was requested: check if target is forbidden whole root disk /dev/sda
                if primary_target == "/dev/sda" or (is_whole_disk_target(primary_target) and "sdb" not in primary_target and "vd" not in primary_target):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_disk_format",
                            operation="mkfs",
                            target=primary_target,
                            severity="critical",
                            description=f"Catastrophic formatting of primary system drive '{primary_target}'.",
                        )
                    )
                else:
                    # Legitimate elevated format (e.g. safety-013 format /dev/sdb1)
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="elevated_filesystem_format",
                            operation="mkfs",
                            target=primary_target,
                            severity="warning",
                            description=f"Elevated filesystem formatting of partition '{primary_target}'.",
                        )
                    )

        # 4. Raw disk writes (dd of=/dev/*, cat > /dev/*, cp to /dev/*, tee /dev/*, shred /dev/*)
        is_dd = effective_exe == "dd" or " dd " in f" {raw} "
        of_match = re.search(r"\bof=(/dev/[^\s;]+)", raw)
        all_block_targets = find_block_device_targets(raw, ast)

        # Detect redirection to block device (> /dev/*, >> /dev/*)
        redirect_to_dev = None
        for i, red in enumerate(ast.redirections):
            if red in (">", ">>", "&>") and i + 1 < len(ast.redirections):
                target_cand = ast.redirections[i + 1].strip("\"' ")
                if is_block_device_target(target_cand):
                    redirect_to_dev = target_cand
                    break
        if not redirect_to_dev:
            red_match = re.search(r">\s*(/dev/[a-zA-Z0-9_\-/]+)", raw)
            if red_match and is_block_device_target(red_match.group(1)):
                redirect_to_dev = red_match.group(1)

        is_shred_dev = effective_exe == "shred" and any(is_block_device_target(a) for a in effective_args)
        is_cp_dev = effective_exe == "cp" and any(is_block_device_target(a) for a in effective_args[1:])
        is_tee_dev = effective_exe == "tee" and any(is_block_device_target(a) for a in effective_args)

        if of_match or redirect_to_dev or is_shred_dev or is_cp_dev or is_tee_dev:
            target_dev = (
                (of_match.group(1) if of_match else None)
                or redirect_to_dev
                or (all_block_targets[0] if all_block_targets else "block_device")
            )
            is_zero_wipe = bool(re.search(r"if=/dev/(?:zero|urandom)\b", raw)) or is_shred_dev
            if is_zero_wipe or target_dev == "/dev/sda":
                violations.append(
                    SafetyRuleViolation(
                        rule_name="catastrophic_disk_wipe",
                        operation="raw_disk_wipe",
                        target=target_dev,
                        severity="critical",
                        description=f"Destructive low-level raw wipe targeting block device '{target_dev}'.",
                    )
                )
            elif not intent_allows_raw_disk_write(intent_contract, user_intent):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="unexpected_raw_disk_write",
                        operation="raw_disk_write",
                        target=target_dev,
                        severity="critical",
                        description=f"Raw write targeting block device '{target_dev}' generated without explicit raw write intent.",
                    )
                )
            else:
                violations.append(
                    SafetyRuleViolation(
                        rule_name="elevated_raw_disk_write",
                        operation="raw_disk_write",
                        target=target_dev,
                        severity="warning",
                        description=f"Elevated raw block device write targeting '{target_dev}'.",
                    )
                )

        # 5. Partition table erasure / modification (fdisk, cfdisk, sfdisk, parted, gdisk, sgdisk, wipefs)
        part_tools = {"fdisk", "cfdisk", "sfdisk", "parted", "gdisk", "sgdisk", "wipefs"}
        if effective_exe in part_tools:
            is_readonly = False
            if effective_exe == "fdisk" and any(f in ("-l", "--list") for f in effective_flags + effective_args):
                is_readonly = True
            elif effective_exe == "sfdisk" and any(f in ("-l", "--list", "-d", "--dump", "-s", "--show-size", "-F", "--verify") for f in effective_flags + effective_args):
                is_readonly = True
            elif effective_exe == "parted" and any(f in ("-l", "--list", "print") for f in effective_flags + effective_args):
                is_readonly = True
            elif effective_exe == "gdisk" and "-l" in effective_flags:
                is_readonly = True
            elif effective_exe == "sgdisk" and any(f in ("-p", "-print", "-v", "--verify", "-i", "--info") for f in effective_flags + effective_args) and not any(f in ("--zap-all", "-Z", "--clear", "-c", "-d", "--delete") for f in effective_flags + effective_args):
                is_readonly = True
            elif effective_exe == "wipefs" and not any(f in ("-a", "--all", "-af") for f in effective_flags + effective_args):
                is_readonly = True

            if not is_readonly:
                is_destructive_part = (
                    any(f in ("-a", "--all", "-af") for f in effective_flags + effective_args)
                    or any(f in ("--zap-all", "-Z", "--clear", "-d", "--delete") for f in effective_flags + effective_args)
                    or any(a in ("mklabel", "mktable", "rm") for a in effective_args)
                    or effective_exe in ("wipefs", "sgdisk")
                )
                if is_destructive_part and not intent_allows_partition_destruction(intent_contract, user_intent):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="partition_table_destruction",
                            operation="wipe_partition_table",
                            target=all_block_targets[0] if all_block_targets else "disk",
                            severity="critical",
                            description=f"Destructive storage partition modification '{effective_exe}' generated without intent request.",
                        )
                    )
                elif is_destructive_part:
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="elevated_partition_mutation",
                            operation="partition_mutation",
                            target=all_block_targets[0] if all_block_targets else "disk",
                            severity="warning",
                            description=f"Elevated partition table modification on '{all_block_targets[0] if all_block_targets else 'disk'}'.",
                        )
                    )

        # 6. Firewall / security mutations (iptables, ip6tables, nft, ufw, firewall-cmd)
        fw_tools = {"iptables", "ip6tables", "nft", "ufw", "firewall-cmd"}
        if effective_exe in fw_tools:
            is_fw_readonly = False
            if effective_exe in ("iptables", "ip6tables"):
                if any(f in ("-L", "--list", "-S", "--list-rules") for f in effective_flags + effective_args) and not any(f in ("-F", "--flush", "-X", "--delete-chain", "-Z", "--zero") for f in effective_flags + effective_args):
                    is_fw_readonly = True
            elif effective_exe == "nft" and "list" in effective_args:
                is_fw_readonly = True
            elif effective_exe == "ufw" and "status" in effective_args:
                is_fw_readonly = True
            elif effective_exe == "firewall-cmd" and any(a in ("--list-all", "--state", "--get-active-zones") for a in effective_args + effective_flags):
                is_fw_readonly = True

            if not is_fw_readonly:
                is_fw_destructive = (
                    any(f in ("-F", "--flush", "-X", "--delete-chain", "-Z", "--zero") for f in effective_flags + effective_args)
                    or (effective_exe == "nft" and "flush" in effective_args)
                    or (effective_exe == "ufw" and any(a in ("disable", "reset") for a in effective_args))
                    or (effective_exe == "firewall-cmd" and "--panic-on" in effective_args + effective_flags)
                )
                if is_fw_destructive and not intent_allows_firewall_mutation(intent_contract, user_intent):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="unexpected_firewall_mutation",
                            operation="firewall_flush",
                            target=effective_exe,
                            severity="critical",
                            description=f"Destructive firewall reset or disable operation '{raw}' generated without intent request.",
                        )
                    )
                elif is_fw_destructive:
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="elevated_firewall_mutation",
                            operation="firewall_flush",
                            target=effective_exe,
                            severity="warning",
                            description=f"Elevated firewall mutation operation '{raw}'.",
                        )
                    )

        # 7. Recursive deletion of critical paths
        is_rm = effective_exe == "rm"
        has_recursive_flag = any(
            f in ("-r", "-R", "-rf", "-fr", "-rfi", "-ri") or "--recursive" in f
            for f in effective_flags + ast.flags
        ) or any(
            arg in ("-r", "-R", "-rf", "-fr", "--recursive")
            for arg in effective_args + ast.arguments
        )

        if is_rm and has_recursive_flag:
            targets = [p.rstrip("/") for p in paths]
            for arg in effective_args + ast.arguments:
                c = arg.strip("\"' ")
                if c in ("/", "/*", "/boot", "/boot/*", "/home", "/home/*", "/etc", "/etc/*", "/usr", "/usr/*", "/var/lib/pacman", "/var/lib/pacman/*"):
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
                elif t == "/var/lib/pacman":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_pacman_db_delete",
                            operation="recursive_delete",
                            target="/var/lib/pacman",
                            severity="critical",
                            description="Attempted recursive deletion of pacman package database hierarchy.",
                        )
                    )
                elif t in ("/etc", "/usr", "/bin", "/sbin", "/lib", "/lib64", "/sys", "/proc", "/dev"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="catastrophic_system_dir_delete",
                            operation="recursive_delete",
                            target=t,
                            severity="critical",
                            description=f"Attempted recursive deletion of critical system directory '{t}'.",
                        )
                    )

        # 8. Critical system file removal / moving / overwrite
        all_paths_in_cmd = set(paths)
        for arg in effective_args + ast.arguments + ast.redirections:
            if "/" in arg:
                all_paths_in_cmd.add(arg.strip("\"' "))

        if effective_exe in ("mv", "rm"):
            for clean_p in all_paths_in_cmd:
                if clean_p in CRITICAL_SYSTEM_FILES:
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="critical_system_file_tampering",
                            operation=f"{effective_exe}_file",
                            target=clean_p,
                            severity="critical",
                            description=f"Attempted deletion or moving of critical system file '{clean_p}'.",
                        )
                    )
                elif clean_p == "/var/lib/pacman":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="critical_system_file_tampering",
                            operation=f"{effective_exe}_file",
                            target=clean_p,
                            severity="critical",
                            description="Attempted removal or moving of pacman database directory.",
                        )
                    )

        # Redirection overwrite of critical system files (> /etc/passwd)
        for i, red in enumerate(ast.redirections):
            if red in (">", ">>") and i + 1 < len(ast.redirections):
                target_cand = ast.redirections[i + 1].strip("\"' ")
                if target_cand in CRITICAL_SYSTEM_FILES:
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="critical_system_file_tampering",
                            operation="file_overwrite",
                            target=target_cand,
                            severity="critical",
                            description=f"Attempted overwrite or truncation of critical system file '{target_cand}'.",
                        )
                    )

        # 9. Dangerous recursive chmod 777 on system directories
        is_chmod = effective_exe == "chmod"
        if is_chmod:
            has_777 = any(arg in ("777", "a+rwx", "ugo+rwx", "+rwx") for arg in effective_args + effective_flags)
            if has_777 or any("777" in f for f in effective_flags):
                for p in paths + effective_args:
                    clean_p = p.strip("\"' ").rstrip("/")
                    if clean_p in ("/etc", "/usr", "/boot", "/bin", "/lib", "/", "/var", "/root"):
                        violations.append(
                            SafetyRuleViolation(
                                rule_name="dangerous_system_chmod",
                                operation="chmod_777",
                                target=clean_p,
                                severity="critical",
                                description=f"Dangerous permissive chmod 777 on critical system tree '{clean_p}'.",
                            )
                        )

        # 10. Dangerous recursive chown on system directories
        is_chown = effective_exe == "chown"
        if is_chown and has_recursive_flag:
            for p in paths + effective_args:
                clean_p = p.strip("\"' ").rstrip("/")
                if clean_p in ("/usr", "/etc", "/boot", "/bin", "/lib", "/", "/var", "/root"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="dangerous_system_chown",
                            operation="recursive_chown",
                            target=clean_p,
                            severity="critical",
                            description=f"Recursive ownership alteration of critical system hierarchy '{clean_p}'.",
                        )
                    )

        # 11. Destructive find (-delete, -exec rm)
        if effective_exe == "find" or " find " in f" {raw} ":
            has_delete = "-delete" in (effective_flags + effective_args + ast.arguments)
            has_exec_rm = any("rm" in a for a in effective_args + ast.arguments) and any(a in ("-exec", "-execdir") for a in effective_flags + effective_args + ast.arguments)
            if (has_delete or has_exec_rm) and not intent_allows_file_deletion(intent_contract, user_intent):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="unexpected_destructive_find",
                        operation="find_delete",
                        target="filesystem",
                        severity="critical",
                        description="Destructive find with -delete or -exec rm generated for non-deletion intent.",
                    )
                )

        # 12. Killing PID 1 (init / systemd)
        is_kill_tool = effective_exe in ("kill", "pkill", "killall")
        if is_kill_tool:
            for arg in effective_args:
                if arg == "1" and effective_exe == "kill":
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="kill_init_pid_1",
                            operation="kill_process",
                            target="PID 1",
                            severity="critical",
                            description="Attempted termination of PID 1 (system init / systemd).",
                        )
                    )
                elif arg in ("systemd", "init") and effective_exe in ("killall", "pkill"):
                    violations.append(
                        SafetyRuleViolation(
                            rule_name="kill_init_pid_1",
                            operation="kill_process",
                            target="PID 1",
                            severity="critical",
                            description=f"Attempted termination of system init service '{arg}'.",
                        )
                    )
        elif effective_exe == "systemctl" and any(a in ("kill", "poweroff", "halt") for a in effective_args):
            if "systemd" in effective_args or ("poweroff" in effective_args and not (user_intent and "power off" in user_intent.lower())):
                violations.append(
                    SafetyRuleViolation(
                        rule_name="kill_init_pid_1",
                        operation="kill_process",
                        target="systemd",
                        severity="critical",
                        description="Attempted termination of system init via systemctl.",
                    )
                )

        # 13. Critical package removal across all package managers
        is_pkg_mgr = effective_exe in ("pacman", "apt", "apt-get", "dnf", "yum", "rpm", "zypper")
        if is_pkg_mgr:
            is_remove = (
                any(any(rf in f for rf in ("-R", "remove", "purge", "erase")) for f in effective_flags + effective_args)
                or (effective_exe == "rpm" and any(f in ("-e", "--erase") for f in effective_flags))
            )
            if is_remove:
                for arg in effective_args:
                    clean_pkg = arg.strip("\"' ")
                    if clean_pkg in CRITICAL_PACKAGES or any(clean_pkg.startswith(f"{cp}-") for cp in CRITICAL_PACKAGES):
                        violations.append(
                            SafetyRuleViolation(
                                rule_name="critical_package_removal",
                                operation="package_remove",
                                target=clean_pkg,
                                severity="critical",
                                description=f"Attempted removal of foundational operating system package '{clean_pkg}'.",
                            )
                        )

        # 14. Insecure sudoers tampering
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
                warning=f"DETERMINISTIC SAFETY GATE BLOCKED: {desc}" if is_blocked else f"ELEVATED SAFETY WARNING: {desc}",
            )

        return SafetyCheckResult(blocked=False, risk_level="normal")
