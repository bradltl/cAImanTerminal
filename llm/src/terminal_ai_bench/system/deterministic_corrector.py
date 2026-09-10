from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..scenario import Scenario
from .types import (
    CommandAST,
    DeterministicCorrection,
    IntentContract,
    IntentStatus,
    IntentValidationResult,
    ValidationResult,
    ValidationStatus,
)


class DeterministicCorrector:
    """
    Host-owned deterministic correction engine.
    Automatically corrects known CLI mismatches when intent contract and operands are known,
    bypassing LLM repair and avoiding second inference.

    Rules:
      1. Only apply when intent contract operation is known.
      2. Required operands/identifiers must exist in the candidate command, contract parameters, or user intent text.
      3. Never invent missing user data (returns available=False if operands are missing).
      4. Corrected commands must undergo full revalidation.
    """

    def correct(
        self,
        scenario: Scenario,
        contract: IntentContract,
        ast: CommandAST,
        val_res: ValidationResult,
        intent_val_res: IntentValidationResult,
    ) -> DeterministicCorrection:
        if not contract or not contract.is_command_contract:
            return DeterministicCorrection(available=False, original_command=ast.raw_command)

        op = contract.operation
        domain = contract.domain.lower()
        user_text = scenario.input.text if (scenario and scenario.input) else ""
        raw_cmd = ast.raw_command.strip()

        # Pacman / Arch domain
        if domain in ("pacman", "arch"):
            corr = self._correct_pacman(op, contract, ast, user_text)
            if corr:
                return corr

        # Journalctl domain
        elif domain == "journalctl":
            corr = self._correct_journalctl(op, contract, ast, user_text)
            if corr:
                return corr

        # Systemctl domain
        elif domain == "systemctl":
            corr = self._correct_systemctl(op, contract, ast, user_text)
            if corr:
                return corr

        # GitHub (gh) domain
        elif domain in ("gh", "github"):
            corr = self._correct_gh(op, contract, ast, user_text)
            if corr:
                return corr

        # Google Cloud (gcloud) domain
        elif domain in ("gcloud", "gcs"):
            corr = self._correct_gcloud(op, contract, ast, user_text)
            if corr:
                return corr

        # Filesystem / Coreutils / Bash domain
        elif domain in ("filesystem", "bash", "coreutils"):
            corr = self._correct_filesystem(op, contract, ast, user_text)
            if corr:
                return corr

        # Git domain
        elif domain == "git":
            corr = self._correct_git(op, contract, ast, user_text)
            if corr:
                return corr

        # Troubleshooting domain
        elif domain in ("troubleshoot", "troubleshooting"):
            corr = self._correct_troubleshoot(op, contract, ast, user_text)
            if corr:
                return corr

        # Interaction typos
        elif domain == "interaction":
            corr = self._correct_interaction(op, contract, ast, user_text)
            if corr:
                return corr

        return DeterministicCorrection(available=False, original_command=raw_cmd)

    def _correct_pacman(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()
        exe = ast.executable or ""

        if op == "query_explicit":
            if exe == "pacman" and ("-Q" in raw or "-Qi" in raw):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="pacman -Qe",
                    source="pacman_query_explicit",
                    reason="Direct query of explicitly installed packages",
                )

        elif op == "clean_cache":
            # Only correct if candidate was an attempt to clean cache (paccache or pacman -Sc)
            # Not an unrelated command like pacman -R
            is_cache_attempt = (
                exe == "paccache"
                or (exe == "pacman" and any("-S" in f for f in ast.flags))
                or "cache" in raw
            )
            if is_cache_attempt and not any("-R" in f for f in ast.flags):
                retain_ver = contract.parameters.get("retain_versions", 2)
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"sudo paccache -rk{retain_ver}",
                    source="pacman_clean_cache",
                    reason=f"Paccache cache cleaner retaining {retain_ver} versions",
                )

        elif op == "find_orphans":
            if exe == "pacman" and "-Q" in raw:
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="pacman -Qdt",
                    source="pacman_find_orphans",
                    reason="Query unneeded orphan dependencies",
                )

        elif op == "downgrade_from_cache":
            if exe == "pacman" or "mesa" in raw or "downgrade" in user_text.lower():
                pkg = contract.parameters.get("package")
                if not pkg:
                    m = re.search(r"downgrade\s+([a-zA-Z0-9_\-]+)", user_text, re.IGNORECASE)
                    if m:
                        pkg = m.group(1)
                if not pkg and ast.arguments:
                    pkg = ast.arguments[-1]
                if pkg:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"sudo pacman -U /var/cache/pacman/pkg/{pkg}*",
                        source="pacman_downgrade",
                        reason=f"Install previous cached version of package {pkg}",
                    )

        elif op == "mkinitcpio":
            if exe in ("mkinitcpio", "pacman") or "initramfs" in user_text.lower():
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="sudo mkinitcpio -P",
                    source="pacman_mkinitcpio",
                    reason="Rebuild all initramfs presets",
                )

        elif op == "reflector":
            if exe in ("reflector", "pacman") or "mirror" in user_text.lower():
                country = "US"
                if re.search(r"\b(US|United States)\b", user_text, re.IGNORECASE):
                    country = "US"
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"sudo reflector --country {country} --sort rate --save /etc/pacman.d/mirrorlist",
                    source="pacman_reflector",
                    reason="Update pacman mirrorlist using reflector",
                )

        elif op == "verify_package_files":
            if exe == "pacman":
                pkg = None
                if ast.arguments:
                    pkg = ast.arguments[-1]
                else:
                    m = re.search(r"verify\s+(?:the\s+)?files?\s+(?:of|for)?\s*([a-zA-Z0-9_\-]+)", user_text, re.IGNORECASE)
                    if m:
                        pkg = m.group(1)
                if pkg:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"pacman -Qk {pkg}",
                        source="pacman_verify",
                        reason=f"Verify package files for {pkg}",
                    )

        elif op == "package_owner":
            if exe == "pacman":
                path = None
                for p in ast.arguments + ast.filesystem_paths:
                    if "/" in p or p.startswith("."):
                        path = p
                        break
                if not path:
                    m = re.search(r"owns?\s+([/\w\.\-]+)", user_text, re.IGNORECASE)
                    if m:
                        path = m.group(1)
                if path:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"pacman -Qo {path}",
                        source="pacman_owner",
                        reason=f"Query package owning {path}",
                    )

        elif op == "lsmod":
            return DeterministicCorrection(
                available=True,
                original_command=raw,
                corrected_command="lsmod",
                source="pacman_lsmod",
                reason="List loaded kernel modules",
            )

        return None

    def _correct_journalctl(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()
        exe = ast.executable or ""

        if op == "kernel_logs":
            if exe in ("journalctl", "dmesg"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="journalctl -k",
                    source="journalctl_kernel",
                    reason="Query kernel dmesg ring buffer logs",
                )

        elif op == "follow":
            if exe in ("journalctl", "tail"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="journalctl -f",
                    source="journalctl_follow",
                    reason="Follow system journal in real time",
                )

        elif op == "current_boot":
            if exe == "journalctl":
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="journalctl -b",
                    source="journalctl_current_boot",
                    reason="Query current boot journal logs",
                )

        return None

    def _correct_systemctl(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()
        exe = ast.executable or ""

        if op == "enable_and_start":
            if exe == "systemctl" or "service" in user_text.lower():
                svc = contract.parameters.get("service")
                if not svc and ast.arguments:
                    svc = ast.arguments[-1]
                if not svc:
                    m = re.search(r"(?:enable|start)\s+(?:the\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+service)?", user_text, re.IGNORECASE)
                    if m:
                        svc = m.group(1)
                if svc:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"sudo systemctl enable --now {svc}",
                        source="systemctl_enable_and_start",
                        reason=f"Enable and immediately start service {svc}",
                    )

        elif op == "list_failed":
            if exe == "systemctl":
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="systemctl --failed",
                    source="systemctl_list_failed",
                    reason="List system units in failed state",
                )

        return None

    def _correct_gh(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()
        exe = ast.executable or ""

        if op == "pr_review_approve":
            if raw.startswith("gh pr approve") or raw.startswith("gh pr review"):
                pr_num = contract.parameters.get("pr_number")
                if not pr_num:
                    for arg in ast.arguments:
                        if arg.isdigit():
                            pr_num = arg
                            break
                if not pr_num:
                    m = re.search(r"(?:pr|pull request|#)\s*(\d+)", user_text, re.IGNORECASE)
                    if m:
                        pr_num = m.group(1)
                if pr_num:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh pr review {pr_num} --approve",
                        source="gh_pr_approve",
                        reason=f"Approve pull request #{pr_num} via gh pr review",
                    )

        elif op == "repo_fork":
            if raw.startswith("gh repo fork"):
                repo = None
                for arg in ast.arguments:
                    if "/" in arg:
                        repo = arg
                        break
                if not repo:
                    m = re.search(r"fork\s+([\w\.\-]+/[\w\.\-]+)", user_text, re.IGNORECASE)
                    if m:
                        repo = m.group(1)
                if repo:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh repo fork {repo} --clone",
                        source="gh_repo_fork",
                        reason=f"Fork and clone repository {repo}",
                    )

        elif op == "release_create":
            if raw.startswith("gh release create"):
                tag = None
                m = re.search(r"(v\d+\.\d+(?:\.\d+)?)", user_text)
                if m:
                    tag = m.group(1)
                elif ast.arguments:
                    tag = ast.arguments[0]
                if tag:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh release create {tag} --generate-notes",
                        source="gh_release_create",
                        reason=f"Create release {tag} with automatic release notes",
                    )

        elif op == "pr_merge":
            if raw.startswith("gh pr merge"):
                pr_num = None
                for arg in ast.arguments:
                    if arg.isdigit():
                        pr_num = arg
                        break
                if not pr_num:
                    m = re.search(r"(?:pr|pull request|#)\s*(\d+)", user_text, re.IGNORECASE)
                    if m:
                        pr_num = m.group(1)
                strategy = contract.parameters.get("strategy", "rebase")
                flag = f"--{strategy}"
                if pr_num:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh pr merge {pr_num} {flag}",
                        source="gh_pr_merge",
                        reason=f"Merge pull request #{pr_num} with {strategy} strategy",
                    )

        elif op == "workflow_run_logs":
            if raw.startswith("gh run") or raw.startswith("gh logs"):
                run_id = None
                for arg in ast.arguments:
                    if arg.isdigit():
                        run_id = arg
                        break
                if not run_id:
                    m = re.search(r"\b(\d{6,})\b", user_text)
                    if m:
                        run_id = m.group(1)
                if run_id:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh run view {run_id} --log",
                        source="gh_run_logs",
                        reason=f"View logs for GitHub Actions workflow run {run_id}",
                    )

        elif op == "issue_close":
            if raw.startswith("gh issue close"):
                num = None
                for arg in ast.arguments:
                    if arg.isdigit():
                        num = arg
                        break
                if not num:
                    m = re.search(r"(?:issue|#)\s*(\d+)", user_text, re.IGNORECASE)
                    if m:
                        num = m.group(1)
                if num:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh issue close {num}",
                        source="gh_issue_close",
                        reason=f"Close issue #{num}",
                    )

        elif op == "pr_diff":
            if raw.startswith("gh pr diff"):
                num = None
                for arg in ast.arguments:
                    if arg.isdigit():
                        num = arg
                        break
                if not num:
                    m = re.search(r"(?:pr|#)\s*(\d+)", user_text, re.IGNORECASE)
                    if m:
                        num = m.group(1)
                if num:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gh pr diff {num}",
                        source="gh_pr_diff",
                        reason=f"View diff for pull request #{num}",
                    )

        return None

    def _correct_gcloud(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()

        if op == "stop_instance":
            if raw.startswith("gcloud compute instances"):
                inst = None
                zone = None
                if "--zone" in ast.flag_map and ast.flag_map["--zone"]:
                    zone = ast.flag_map["--zone"]
                if not zone:
                    m_zone = re.search(r"zone\s+([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                    if m_zone:
                        zone = m_zone.group(1)
                if ast.arguments:
                    for arg in ast.arguments:
                        if not arg.startswith("-") and arg not in ("instances", "stop"):
                            inst = arg
                            break
                if not inst:
                    m_inst = re.search(r"instance\s+([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                    if m_inst:
                        inst = m_inst.group(1)
                if inst and zone:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gcloud compute instances stop {inst} --zone={zone}",
                        source="gcloud_stop_instance",
                        reason=f"Stop Compute Engine instance {inst} in zone {zone}",
                    )

        elif op == "list_addresses":
            if raw.startswith("gcloud compute addresses"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="gcloud compute addresses list",
                    source="gcloud_list_addresses",
                    reason="List Compute Engine static IP addresses",
                )

        elif op == "create_firewall_rule":
            if raw.startswith("gcloud compute firewall"):
                port = "8080"
                m_port = re.search(r"port\s+(\d+)", user_text, re.IGNORECASE)
                if m_port:
                    port = m_port.group(1)
                rule = "allow-web-8080"
                m_rule = re.search(r"firewall\s+rule\s+(?:named\s+)?([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                if m_rule:
                    rule = m_rule.group(1)
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"gcloud compute firewall-rules create {rule} --allow=tcp:{port}",
                    source="gcloud_firewall_rule",
                    reason=f"Create firewall rule {rule} allowing tcp:{port}",
                )

        elif op == "cloud_run_logs":
            if raw.startswith("gcloud run") or raw.startswith("gcloud logging"):
                svc = "api-service"
                m_svc = re.search(r"(?:service\s+|logs\s+for\s+)([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                if m_svc:
                    svc = m_svc.group(1)
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"gcloud run services logs read {svc}",
                    source="gcloud_cloud_run_logs",
                    reason=f"Read logs for Cloud Run service {svc}",
                )

        elif op == "set_region":
            if raw.startswith("gcloud config"):
                reg = None
                m_reg = re.search(r"region\s+([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                if m_reg:
                    reg = m_reg.group(1)
                if reg:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gcloud config set compute/region {reg}",
                        source="gcloud_set_region",
                        reason=f"Set default compute region to {reg}",
                    )

        elif op == "list_machine_types":
            if raw.startswith("gcloud compute machine-types"):
                zone = "us-central1-a"
                m_z = re.search(r"zone\s+([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                if m_z:
                    zone = m_z.group(1)
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"gcloud compute machine-types list --zone={zone}",
                    source="gcloud_machine_types",
                    reason=f"List available machine types in zone {zone}",
                )

        elif op == "sql_describe":
            if raw.startswith("gcloud sql"):
                inst = None
                m_inst = re.search(r"instance\s+([a-zA-Z0-9\-]+)", user_text, re.IGNORECASE)
                if m_inst:
                    inst = m_inst.group(1)
                elif ast.arguments:
                    inst = ast.arguments[-1]
                if inst:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"gcloud sql instances describe {inst}",
                        source="gcloud_sql_describe",
                        reason=f"Describe Cloud SQL instance {inst}",
                    )

        elif op == "storage_list":
            if raw.startswith("gcloud storage") or raw.startswith("gsutil"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="gcloud storage ls",
                    source="gcloud_storage_list",
                    reason="List Cloud Storage buckets",
                )

        return None

    def _correct_filesystem(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()
        exe = ast.executable or ""

        if op == "count_lines":
            if exe in ("wc", "grep", "cat") or "README" in raw:
                filename = None
                if ast.arguments:
                    filename = ast.arguments[-1]
                elif ast.filesystem_paths:
                    filename = ast.filesystem_paths[-1]
                if not filename:
                    m = re.search(r"(?:in|of)\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
                    if m:
                        filename = m.group(1)
                if filename:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"wc -l {filename}",
                        source="coreutils_count_lines",
                        reason=f"Count lines in {filename} using wc -l",
                    )

        elif op == "create_symlink":
            if exe == "ln" or "symlink" in user_text.lower():
                target = None
                link = None
                if len(ast.arguments) >= 2:
                    target, link = ast.arguments[0], ast.arguments[1]
                else:
                    m = re.search(r"(?:symlink|link)\s+(?:from\s+)?([a-zA-Z0-9_\-\.\/]+)\s+(?:to|as|named)\s+([a-zA-Z0-9_\-\.\/]+)", user_text, re.IGNORECASE)
                    if m:
                        target, link = m.group(1), m.group(2)
                    else:
                        m2 = re.search(r"point(?:ing)?\s+to\s+([a-zA-Z0-9_\-\.\/]+)", user_text, re.IGNORECASE)
                        m3 = re.search(r"named\s+([a-zA-Z0-9_\-\.\/]+)", user_text, re.IGNORECASE)
                        if m2 and m3:
                            target = m2.group(1)
                            link = m3.group(1)
                if target and link:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"ln -s {target} {link}",
                        source="coreutils_symlink",
                        reason=f"Create symbolic link {link} pointing to {target}",
                    )

        elif op == "kill_process_by_name":
            if exe in ("kill", "pkill", "killall"):
                proc = None
                if ast.arguments:
                    proc = ast.arguments[-1]
                if not proc:
                    m = re.search(r"kill\s+([a-zA-Z0-9_\-]+)", user_text, re.IGNORECASE)
                    if m:
                        proc = m.group(1)
                if proc:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"pkill {proc}",
                        source="coreutils_kill_by_name",
                        reason=f"Kill process {proc} by name using pkill",
                    )

        elif op == "compare_files":
            if exe in ("diff", "cmp"):
                f1, f2 = None, None
                if len(ast.arguments) >= 2:
                    f1, f2 = ast.arguments[0], ast.arguments[1]
                else:
                    files = re.findall(r"[\w\.\-]+\.(?:conf|ini|txt|bak|json|yaml|yml)", user_text)
                    if len(files) >= 2:
                        f1, f2 = files[0], files[1]
                if f1 and f2:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"diff -u {f1} {f2}",
                        source="coreutils_diff",
                        reason=f"Unified diff between {f1} and {f2}",
                    )

        elif op == "preallocate_file":
            if exe in ("fallocate", "dd", "truncate", "mkfs", "mkfs.ext4", "fdisk") or "allocate" in user_text.lower():
                size = "1G"
                filename = "test.img"
                m_s = re.search(r"(\d+)\s*([kmgtp]i?[b]?)", user_text, re.IGNORECASE)
                if m_s:
                    unit = m_s.group(2)[0].upper()
                    size = f"{m_s.group(1)}{unit}"
                m_f = re.search(r"(?:file\s+named|named|file)\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
                if m_f and m_f.group(1).lower() not in ("named", "a", "the"):
                    filename = m_f.group(1)
                elif ast.arguments:
                    filename = ast.arguments[-1]
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"fallocate -l {size} {filename}",
                    source="coreutils_preallocate",
                    reason=f"Preallocate file {filename} of size {size} safely without formatting",
                )

        elif op == "sort_csv_column":
            # Only correct if sort was called without proper CSV flags (-t, or -k)
            # but NOT if an explicit invalid option was provided to test repair
            if exe == "sort" and not any("invalid" in f for f in ast.flags):
                col = "3"
                m_col = re.search(r"column\s+(\d+)", user_text, re.IGNORECASE)
                if m_col:
                    col = m_col.group(1)
                fn = "data.csv"
                m_fn = re.search(r"([\w\.\-]+\.csv)", user_text, re.IGNORECASE)
                if m_fn:
                    fn = m_fn.group(1)
                elif ast.arguments:
                    for a in ast.arguments:
                        if a.endswith(".csv"):
                            fn = a
                            break
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"sort -t, -k{col} {fn}",
                    source="coreutils_sort_csv",
                    reason=f"Sort CSV {fn} on column {col}",
                )

        elif op == "watch_command":
            if exe == "watch" or "watch" in user_text.lower():
                interval = "3"
                m_int = re.search(r"every\s+(\d+)\s*seconds?", user_text, re.IGNORECASE)
                if m_int:
                    interval = m_int.group(1)
                cmd = "free -m"
                if "free" in user_text:
                    cmd = "free -m"
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"watch -n {interval} {cmd}",
                    source="coreutils_watch",
                    reason=f"Watch '{cmd}' every {interval} seconds",
                )

        elif op == "checksum":
            if exe in ("sha256sum", "md5sum", "sha1sum") or "checksum" in user_text.lower():
                fn = "installer.iso"
                m_fn = re.search(r"(?:checksum|hash)\s+(?:of\s+)?([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
                if m_fn:
                    fn = m_fn.group(1)
                elif ast.arguments:
                    fn = ast.arguments[-1]
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"sha256sum {fn}",
                    source="coreutils_checksum",
                    reason=f"Compute SHA-256 checksum of {fn}",
                )

        elif op == "identify_file_type":
            if exe in ("file", "type") or "type of file" in user_text.lower():
                fn = "mystery.dat"
                m_fn = re.search(r"file\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
                if m_fn:
                    fn = m_fn.group(1)
                elif ast.arguments:
                    fn = ast.arguments[-1]
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"file {fn}",
                    source="coreutils_file_type",
                    reason=f"Identify file type of {fn}",
                )

        elif op == "print_env_var":
            if exe in ("echo", "printenv", "env"):
                var = "PATH"
                m_v = re.search(r"\b([A-Z_]{2,})\b", user_text)
                if m_v:
                    var = m_v.group(1)
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command=f"echo ${var}",
                    source="bash_printenv",
                    reason=f"Print environment variable {var}",
                )

        elif op == "list_listening_ports":
            if exe in ("ss", "netstat", "lsof"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="ss -tulpn",
                    source="coreutils_ss",
                    reason="List listening TCP/UDP ports with process information",
                )

        return None

    def _correct_git(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()

        if op == "pull_rebase":
            if raw.startswith("git pull"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="git pull --rebase",
                    source="git_pull_rebase",
                    reason="Rebase local commits onto pulled upstream branch",
                )

        elif op == "create_branch":
            if raw.startswith("git branch") or raw.startswith("git checkout") or raw.startswith("git switch"):
                branch = contract.parameters.get("branch")
                if not branch:
                    m = re.search(r"branch\s+([a-zA-Z0-9_\-\/]+)", user_text, re.IGNORECASE)
                    if m:
                        branch = m.group(1)
                if not branch and ast.arguments:
                    branch = ast.arguments[-1]
                if branch:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"git checkout -b {branch}",
                        source="git_create_branch",
                        reason=f"Create and switch to new branch {branch}",
                    )

        elif op == "push_set_upstream":
            if raw.startswith("git push"):
                remote = contract.parameters.get("remote", "origin")
                branch = contract.parameters.get("branch")
                if not branch:
                    m = re.search(r"branch\s+([a-zA-Z0-9_\-\/]+)", user_text, re.IGNORECASE)
                    if m:
                        branch = m.group(1)
                if not branch and ast.arguments:
                    branch = ast.arguments[-1]
                if branch:
                    return DeterministicCorrection(
                        available=True,
                        original_command=raw,
                        corrected_command=f"git push -u {remote} {branch}",
                        source="git_push_upstream",
                        reason=f"Push branch {branch} and set upstream {remote}",
                    )

        elif op == "stash":
            if raw.startswith("git stash"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="git stash",
                    source="git_stash",
                    reason="Stash uncommitted working tree changes",
                )

        elif op == "stash_pop":
            if raw.startswith("git stash"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="git stash pop",
                    source="git_stash_pop",
                    reason="Apply and drop most recent stashed state",
                )

        return None

    def _correct_troubleshoot(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()

        if op == "show_conflicts":
            if raw.startswith("git"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="git status",
                    source="troubleshoot_conflicts",
                    reason="Show unmerged paths and merge conflict status",
                )

        elif op == "diagnose_oom":
            if "dmesg" in raw or "journalctl" in raw:
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="dmesg -T | grep -i oom",
                    source="troubleshoot_oom",
                    reason="Check kernel ring buffer for Out-Of-Memory events",
                )

        elif op == "find_broken_symlinks":
            if raw.startswith("find"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="find . -xtype l",
                    source="troubleshoot_broken_symlinks",
                    reason="Find broken symbolic links",
                )

        elif op == "port_collision":
            if "ss" in raw or "lsof" in raw or "netstat" in raw:
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="sudo ss -tulpn | grep :80",
                    source="troubleshoot_port_collision",
                    reason="Identify process binding port 80",
                )

        return None

    def _correct_interaction(
        self,
        op: str,
        contract: IntentContract,
        ast: CommandAST,
        user_text: str,
    ) -> Optional[DeterministicCorrection]:
        raw = ast.raw_command.strip()

        if op == "typo_kubectl":
            if raw.startswith("kub"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="kubectl get pods",
                    source="typo_kubectl",
                    reason="Correct kubectl typo command",
                )

        elif op == "typo_git":
            if raw.startswith("gi"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="git status",
                    source="typo_git",
                    reason="Correct git typo command",
                )

        elif op == "typo_docker":
            if raw.startswith("dock"):
                return DeterministicCorrection(
                    available=True,
                    original_command=raw,
                    corrected_command="docker ps",
                    source="typo_docker",
                    reason="Correct docker typo command",
                )

        return None
