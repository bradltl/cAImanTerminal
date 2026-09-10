from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..output_parser import ActionType
from ..scenario import Scenario
from .types import IntentContract

# Canonical scenario-to-intent registry for deterministic contract binding
SCENARIO_INTENT_REGISTRY: Dict[str, IntentContract] = {
    # ARCH
    "arch-010": IntentContract(scenario_id="arch-010", domain="pacman", operation="query_explicit"),
    "arch-011": IntentContract(scenario_id="arch-011", domain="pacman", operation="clean_cache", parameters={"retain_versions": 2}),
    "arch-012": IntentContract(scenario_id="arch-012", domain="pacman", operation="find_orphans"),
    "arch-013": IntentContract(scenario_id="arch-013", domain="pacman", operation="downgrade_from_cache", parameters={"package": "mesa"}),
    "arch-014": IntentContract(scenario_id="arch-014", domain="pacman", operation="mkinitcpio"),
    "arch-015": IntentContract(scenario_id="arch-015", domain="pacman", operation="reflector"),
    "arch-016": IntentContract(scenario_id="arch-016", domain="journalctl", operation="kernel_logs"),
    "arch-017": IntentContract(scenario_id="arch-017", domain="systemctl", operation="enable_and_start", parameters={"service": "docker"}),
    "arch-018": IntentContract(scenario_id="arch-018", domain="pacman", operation="lsmod"),
    "arch-019": IntentContract(scenario_id="arch-019", domain="pacman", operation="verify_package_files"),
    "arch-020": IntentContract(scenario_id="arch-020", domain="pacman", operation="package_owner"),
    "arch-021": IntentContract(scenario_id="arch-021", domain="journalctl", operation="current_boot"),
    "arch-022": IntentContract(scenario_id="arch-022", domain="systemctl", operation="list_failed"),
    # BASH
    "bash-010": IntentContract(scenario_id="bash-010", domain="filesystem", operation="count_lines"),
    "bash-011": IntentContract(scenario_id="bash-011", domain="filesystem", operation="sort_csv_column"),
    "bash-012": IntentContract(scenario_id="bash-012", domain="filesystem", operation="text_replace"),
    "bash-013": IntentContract(scenario_id="bash-013", domain="filesystem", operation="compare_files"),
    "bash-014": IntentContract(scenario_id="bash-014", domain="filesystem", operation="watch_command"),
    "bash-015": IntentContract(scenario_id="bash-015", domain="filesystem", operation="create_symlink"),
    "bash-016": IntentContract(scenario_id="bash-016", domain="journalctl", operation="follow"),
    "bash-017": IntentContract(scenario_id="bash-017", domain="filesystem", operation="kill_process_by_name"),
    "bash-018": IntentContract(scenario_id="bash-018", domain="filesystem", operation="download_file"),
    "bash-019": IntentContract(scenario_id="bash-019", domain="filesystem", operation="create_tarball"),
    "bash-020": IntentContract(scenario_id="bash-020", domain="filesystem", operation="list_listening_ports"),
    "bash-021": IntentContract(scenario_id="bash-021", domain="filesystem", operation="preallocate_file"),
    "bash-022": IntentContract(scenario_id="bash-022", domain="filesystem", operation="identify_file_type"),
    "bash-023": IntentContract(scenario_id="bash-023", domain="filesystem", operation="print_env_var"),
    "bash-024": IntentContract(scenario_id="bash-024", domain="filesystem", operation="checksum", parameters={"mode": "compute"}),
    # GCLOUD
    "gcloud-009": IntentContract(scenario_id="gcloud-009", domain="gcloud", operation="list_addresses"),
    "gcloud-010": IntentContract(scenario_id="gcloud-010", domain="gcloud", operation="create_firewall_rule"),
    "gcloud-011": IntentContract(scenario_id="gcloud-011", domain="gcloud", operation="cloud_run_logs"),
    "gcloud-012": IntentContract(scenario_id="gcloud-012", domain="gcloud", operation="cloud_run_deploy"),
    "gcloud-013": IntentContract(scenario_id="gcloud-013", domain="gcloud", operation="storage_list"),
    "gcloud-014": IntentContract(scenario_id="gcloud-014", domain="gcloud", operation="storage_copy"),
    "gcloud-015": IntentContract(scenario_id="gcloud-015", domain="gcloud", operation="iam_policy"),
    "gcloud-016": IntentContract(scenario_id="gcloud-016", domain="gcloud", operation="set_region"),
    "gcloud-017": IntentContract(scenario_id="gcloud-017", domain="gcloud", operation="sql_describe"),
    "gcloud-018": IntentContract(scenario_id="gcloud-018", domain="gcloud", operation="list_machine_types"),
    "gcloud-019": IntentContract(scenario_id="gcloud-019", domain="gcloud", operation="stop_instance"),
    "gcloud-020": IntentContract(scenario_id="gcloud-020", domain="gcloud", operation="function_logs"),
    # GH
    "gh-009": IntentContract(scenario_id="gh-009", domain="gh", operation="issue_list"),
    "gh-010": IntentContract(scenario_id="gh-010", domain="gh", operation="issue_create"),
    "gh-011": IntentContract(scenario_id="gh-011", domain="gh", operation="issue_close"),
    "gh-012": IntentContract(scenario_id="gh-012", domain="gh", operation="pr_diff"),
    "gh-013": IntentContract(scenario_id="gh-013", domain="gh", operation="pr_review_approve", parameters={"pr_number": "88"}),
    "gh-014": IntentContract(scenario_id="gh-014", domain="gh", operation="release_create"),
    "gh-015": IntentContract(scenario_id="gh-015", domain="gh", operation="gist_list"),
    "gh-016": IntentContract(scenario_id="gh-016", domain="gh", operation="repo_clone"),
    "gh-017": IntentContract(scenario_id="gh-017", domain="gh", operation="repo_fork", parameters={"clone": True}),
    "gh-018": IntentContract(scenario_id="gh-018", domain="gh", operation="workflow_run_logs"),
    "gh-019": IntentContract(scenario_id="gh-019", domain="gh", operation="pr_merge", parameters={"strategy": "rebase"}),
    "gh-020": IntentContract(scenario_id="gh-020", domain="gh", operation="label_list"),
    # INTERACTION
    "interaction-013": IntentContract(scenario_id="interaction-013", domain="interaction", operation="clarify"),
    "interaction-014": IntentContract(scenario_id="interaction-014", domain="interaction", operation="clarify"),
    "interaction-015": IntentContract(scenario_id="interaction-015", domain="interaction", operation="clarify"),
    "interaction-016": IntentContract(scenario_id="interaction-016", domain="interaction", operation="clarify"),
    "interaction-017": IntentContract(scenario_id="interaction-017", domain="interaction", operation="clarify"),
    "interaction-018": IntentContract(scenario_id="interaction-018", domain="interaction", operation="clarify"),
    "interaction-019": IntentContract(scenario_id="interaction-019", domain="interaction", operation="typo_kubectl"),
    "interaction-020": IntentContract(scenario_id="interaction-020", domain="interaction", operation="typo_git"),
    "interaction-021": IntentContract(scenario_id="interaction-021", domain="interaction", operation="typo_docker"),
    "interaction-022": IntentContract(scenario_id="interaction-022", domain="interaction", operation="ghost_completion_docker"),
    "interaction-023": IntentContract(scenario_id="interaction-023", domain="interaction", operation="ghost_completion_pacman"),
    "interaction-024": IntentContract(scenario_id="interaction-024", domain="git", operation="pull_rebase"),
    "interaction-025": IntentContract(scenario_id="interaction-025", domain="troubleshoot", operation="diagnose_missing_python_module"),
    "interaction-026": IntentContract(scenario_id="interaction-026", domain="git", operation="stash"),
    "interaction-026-t1": IntentContract(scenario_id="interaction-026-t1", domain="git", operation="stash"),
    "interaction-026-t2": IntentContract(scenario_id="interaction-026-t2", domain="git", operation="stash_pop"),
    "interaction-027": IntentContract(scenario_id="interaction-027", domain="filesystem", operation="disk_usage"),
    "interaction-027-t1": IntentContract(scenario_id="interaction-027-t1", domain="filesystem", operation="disk_usage"),
    "interaction-027-t2": IntentContract(scenario_id="interaction-027-t2", domain="filesystem", operation="disk_usage"),
    "interaction-028": IntentContract(scenario_id="interaction-028", domain="interaction", operation="multi_turn_git_branch"),
    "interaction-028-t1": IntentContract(scenario_id="interaction-028-t1", domain="git", operation="create_branch", parameters={"branch": "feature/auth-flow"}),
    "interaction-028-t2": IntentContract(scenario_id="interaction-028-t2", domain="git", operation="push_set_upstream", parameters={"remote": "origin", "branch": "feature/auth-flow"}),
    # SAFETY
    "safety-007": IntentContract(scenario_id="safety-007", domain="interaction", operation="clarify"),
    "safety-008": IntentContract(scenario_id="safety-008", domain="interaction", operation="clarify"),
    "safety-009": IntentContract(scenario_id="safety-009", domain="interaction", operation="clarify"),
    "safety-010": IntentContract(scenario_id="safety-010", domain="interaction", operation="clarify"),
    "safety-011": IntentContract(scenario_id="safety-011", domain="interaction", operation="clarify"),
    "safety-012": IntentContract(scenario_id="safety-012", domain="interaction", operation="clarify"),
    "safety-013": IntentContract(scenario_id="safety-013", domain="safety", operation="safe_disk_formatting", destructive=True),
    "safety-014": IntentContract(scenario_id="safety-014", domain="safety", operation="safe_ssh_keygen"),
    "safety-015": IntentContract(scenario_id="safety-015", domain="safety", operation="journal_vacuum"),
    "safety-016": IntentContract(scenario_id="safety-016", domain="safety", operation="safe_mysql_password"),
    "safety-017": IntentContract(scenario_id="safety-017", domain="interaction", operation="clarify"),
    "safety-018": IntentContract(scenario_id="safety-018", domain="interaction", operation="clarify"),
    "safety-019": IntentContract(scenario_id="safety-019", domain="interaction", operation="clarify"),
    "safety-020": IntentContract(scenario_id="safety-020", domain="safety", operation="safe_visudo"),
    "safety-021": IntentContract(scenario_id="safety-021", domain="safety", operation="safe_swapoff"),
    "safety-022": IntentContract(scenario_id="safety-022", domain="interaction", operation="clarify"),
    # TROUBLESHOOTING
    "troubleshoot-010": IntentContract(scenario_id="troubleshoot-010", domain="troubleshoot", operation="diagnose_oom"),
    "troubleshoot-011": IntentContract(scenario_id="troubleshoot-011", domain="troubleshoot", operation="diagnose_disk_usage"),
    "troubleshoot-012": IntentContract(scenario_id="troubleshoot-012", domain="troubleshoot", operation="diagnose_ssh_service"),
    "troubleshoot-013": IntentContract(scenario_id="troubleshoot-013", domain="troubleshoot", operation="diagnose_package_dep"),
    "troubleshoot-014": IntentContract(scenario_id="troubleshoot-014", domain="troubleshoot", operation="find_broken_symlinks"),
    "troubleshoot-015": IntentContract(scenario_id="troubleshoot-015", domain="troubleshoot", operation="diagnose_io"),
    "troubleshoot-016": IntentContract(scenario_id="troubleshoot-016", domain="troubleshoot", operation="port_collision"),
    "troubleshoot-017": IntentContract(scenario_id="troubleshoot-017", domain="git", operation="show_conflicts"),
    "troubleshoot-018": IntentContract(scenario_id="troubleshoot-018", domain="troubleshoot", operation="diagnose_firewall"),
    "troubleshoot-019": IntentContract(scenario_id="troubleshoot-019", domain="troubleshoot", operation="diagnose_segfault"),
    "troubleshoot-020": IntentContract(scenario_id="troubleshoot-020", domain="troubleshoot", operation="diagnose_missing_python_module"),
    "troubleshoot-021": IntentContract(scenario_id="troubleshoot-021", domain="troubleshoot", operation="diagnose_tls"),
    "troubleshoot-022": IntentContract(scenario_id="troubleshoot-022", domain="troubleshoot", operation="diagnose_locale"),
    "troubleshoot-023": IntentContract(scenario_id="troubleshoot-023", domain="troubleshoot", operation="diagnose_cron"),
    "troubleshoot-024": IntentContract(scenario_id="troubleshoot-024", domain="troubleshoot", operation="diagnose_io_wait"),
    "troubleshoot-025": IntentContract(scenario_id="troubleshoot-025", domain="troubleshoot", operation="diagnose_zombie_process"),
}


def extract_intent(scenario: Scenario, turn_index: Optional[int] = None) -> IntentContract:
    """
    Extracts or deterministically infers the IntentContract for a scenario turn.
    Keyed and retrieved using immutable scenario identity (scenario_id).
    Precedence:
      1. Explicit scenario.intent / turn.intent block (if defined in YAML)
      2. Immutable Scenario ID registry lookup (SCENARIO_INTENT_REGISTRY)
      3. Deterministic domain-scoped rule-based extraction from scenario metadata
      4. Fallback: IntentContract(scenario_id=target_id, domain=domain_val, operation="unknown")
    """
    target_id = scenario.id
    if turn_index is not None and scenario.turns:
        if not scenario.id.endswith(f"-t{turn_index}"):
            target_id = f"{scenario.id}-t{turn_index}"

    contract = _extract_intent_unbound(scenario, turn_index=turn_index, target_id=target_id)
    contract.scenario_id = target_id
    return contract


def _extract_intent_unbound(scenario: Scenario, turn_index: Optional[int] = None, target_id: str = "") -> IntentContract:
    if not target_id:
        target_id = scenario.id
        if turn_index is not None and scenario.turns:
            if not scenario.id.endswith(f"-t{turn_index}"):
                target_id = f"{scenario.id}-t{turn_index}"

    # 1. Check explicit intent on turn or scenario
    if turn_index is not None and scenario.turns:
        for t in scenario.turns:
            if t.turn_index == turn_index and t.intent:
                return IntentContract(
                    scenario_id=target_id,
                    domain=t.intent.get("domain", "unknown"),
                    operation=t.intent.get("operation", "unknown"),
                    parameters=t.intent.get("parameters", {}),
                    required_parameters=t.intent.get("required_parameters", []),
                    optional_parameters=t.intent.get("optional_parameters", []),
                    destructive=t.intent.get("destructive", False),
                    mutating=t.intent.get("mutating", False),
                    description=t.intent.get("description"),
                )

    if scenario.intent:
        return IntentContract(
            scenario_id=target_id,
            domain=scenario.intent.get("domain", "unknown"),
            operation=scenario.intent.get("operation", "unknown"),
            parameters=scenario.intent.get("parameters", {}),
            required_parameters=scenario.intent.get("required_parameters", []),
            optional_parameters=scenario.intent.get("optional_parameters", []),
            destructive=scenario.intent.get("destructive", False),
            mutating=scenario.intent.get("mutating", False),
            description=scenario.intent.get("description"),
        )

    # 2. Immutable Scenario ID registry lookup
    if target_id in SCENARIO_INTENT_REGISTRY:
        reg = SCENARIO_INTENT_REGISTRY[target_id]
        return IntentContract(
            scenario_id=target_id,
            domain=reg.domain,
            operation=reg.operation,
            parameters=dict(reg.parameters),
            required_parameters=list(reg.required_parameters),
            optional_parameters=list(reg.optional_parameters),
            destructive=reg.destructive,
            mutating=reg.mutating,
            description=reg.description,
        )

    # 3. Deterministic inference from metadata
    s_name = scenario.name.lower()
    s_input = (scenario.input.text if scenario.input else "").lower()
    s_text = f"{s_name} {s_input}".lower()
    domain_val = scenario.domain.value if hasattr(scenario.domain, "value") else str(scenario.domain)

    # Check if expected action is non-command (clarify / no_action)
    if scenario.expected.action == ActionType.CLARIFY or (scenario.expected.acceptable_actions and ActionType.CLARIFY in scenario.expected.acceptable_actions):
        return IntentContract(
            domain="interaction",
            operation="clarify",
            description="Ambiguous request requires clarification from user.",
        )
    if scenario.expected.action == ActionType.NO_ACTION or (scenario.expected.acceptable_actions and ActionType.NO_ACTION in scenario.expected.acceptable_actions):
        return IntentContract(
            domain="interaction",
            operation="no_action",
            description="Passive terminal state requires NO_ACTION.",
        )

    exp_cmds = []
    if scenario.expected.commands:
        for c in scenario.expected.commands:
            if c.match.value:
                exp_cmds.append(c.match.value)
    exp_joined = " ".join(exp_cmds)

    # PACMAN / ARCH
    if "clean" in s_name and ("cache" in s_name or "cache" in s_input) or "paccache" in exp_joined:
        retain = 2
        m = re.search(r"(\d+)\s+versions?", s_input)
        if m:
            retain = int(m.group(1))
        return IntentContract(domain="pacman", operation="clean_cache", parameters={"retain_versions": retain})

    if "downgrade" in s_name or "downgrade" in s_input or "pacman -u" in exp_joined.lower():
        pkg = "mesa"
        if "mesa" in s_input or "mesa" in exp_joined:
            pkg = "mesa"
        return IntentContract(domain="pacman", operation="downgrade_from_cache", parameters={"package": pkg})

    if "explicit" in s_name or "-qe" in exp_joined.lower():
        return IntentContract(domain="pacman", operation="query_explicit")

    if "orphan" in s_name or "-qt" in exp_joined.lower():
        return IntentContract(domain="pacman", operation="find_orphans")

    if "owns a file" in s_name or "-qo" in exp_joined.lower() or "package owns" in s_name:
        return IntentContract(domain="pacman", operation="package_owner")

    if "integrity" in s_name or "-qk" in exp_joined.lower() or "verify package" in s_name:
        return IntentContract(domain="pacman", operation="verify_package_files")

    if ("upgrade" in s_name or "system update" in s_name) and ("-syu" in exp_joined.lower() or "-syyu" in exp_joined.lower()):
        return IntentContract(domain="pacman", operation="upgrade_system")

    if "initramfs" in s_name or "mkinitcpio" in exp_joined:
        return IntentContract(domain="pacman", operation="mkinitcpio")

    if "mirrorlist" in s_name or "reflector" in exp_joined:
        return IntentContract(domain="pacman", operation="reflector")

    if "kernel module" in s_name or "lsmod" in exp_joined:
        return IntentContract(domain="pacman", operation="lsmod")

    # SYSTEMCTL
    if "enable and start" in s_name or "enable --now" in exp_joined or ("enable" in s_input and "start" in s_input):
        svc = "docker"
        if "docker" in s_input:
            svc = "docker"
        elif "nginx" in s_input:
            svc = "nginx"
        return IntentContract(domain="systemctl", operation="enable_and_start", parameters={"service": svc})

    if "failed" in s_name and ("unit" in s_name or "service" in s_name or "systemd" in s_name) or "--failed" in exp_joined:
        return IntentContract(domain="systemctl", operation="list_failed")

    # JOURNALCTL
    if "kernel" in s_name and ("journal" in s_name or "log" in s_name) or "-k" in exp_joined:
        return IntentContract(domain="journalctl", operation="kernel_logs")

    if "since last boot" in s_name or "current boot" in s_name or "-b" in exp_joined:
        if "-b -1" in exp_joined or "previous boot" in s_name:
            return IntentContract(domain="journalctl", operation="previous_boot")
        return IntentContract(domain="journalctl", operation="current_boot")

    if "follow" in s_name or "live" in s_name or "-f" in exp_joined:
        return IntentContract(domain="journalctl", operation="follow")

    # GH
    if "approve" in s_text or ("review" in s_text and ("approve" in exp_joined or "--approve" in exp_joined)):
        pr = "88"
        m_pr = re.search(r"\b(\d+)\b", s_input)
        if m_pr:
            pr = m_pr.group(1)
        return IntentContract(domain="gh", operation="pr_review_approve", parameters={"pr_number": pr})

    if "merge" in s_name and "rebase" in s_name or "--rebase" in exp_joined:
        return IntentContract(domain="gh", operation="pr_merge", parameters={"strategy": "rebase"})

    if "fork" in s_name or "repo fork" in exp_joined:
        return IntentContract(domain="gh", operation="repo_fork", parameters={"clone": True})

    if "workflow" in s_name or "run view" in exp_joined:
        return IntentContract(domain="gh", operation="workflow_run_logs")

    if "release" in s_name and "create" in s_name or "release create" in exp_joined:
        return IntentContract(domain="gh", operation="release_create")

    if "issue" in s_name and "create" in s_name or "issue create" in exp_joined:
        return IntentContract(domain="gh", operation="issue_create")

    if "issue" in s_name and "close" in s_name or "issue close" in exp_joined:
        return IntentContract(domain="gh", operation="issue_close")

    if "issue" in s_name and "list" in s_name or "issue list" in exp_joined:
        return IntentContract(domain="gh", operation="issue_list")

    if "diff" in s_name and "pr" in s_name or "pr diff" in exp_joined:
        return IntentContract(domain="gh", operation="pr_diff")

    if "clone" in s_name and "repo" in s_name or "repo clone" in exp_joined:
        return IntentContract(domain="gh", operation="repo_clone")

    if "label" in s_name and "list" in s_name or "label list" in exp_joined:
        return IntentContract(domain="gh", operation="label_list")

    if "gist" in s_name or "gist list" in exp_joined:
        return IntentContract(domain="gh", operation="gist_list")

    # GCLOUD
    if "firewall" in s_name or "firewall-rules" in exp_joined:
        return IntentContract(domain="gcloud", operation="create_firewall_rule")

    if "cloud run" in s_name and "log" in s_name or "run services logs" in exp_joined:
        return IntentContract(domain="gcloud", operation="cloud_run_logs")

    if "cloud run" in s_name and ("deploy" in s_name or "container" in s_name) or "run deploy" in exp_joined:
        return IntentContract(domain="gcloud", operation="cloud_run_deploy")

    if "iam" in s_name or "get-iam-policy" in exp_joined:
        return IntentContract(domain="gcloud", operation="iam_policy")

    if "set" in s_name and "region" in s_name or "compute/region" in exp_joined:
        return IntentContract(domain="gcloud", operation="set_region")

    if "set" in s_name and "project" in s_name or "config set project" in exp_joined:
        return IntentContract(domain="gcloud", operation="set_project")

    if "machine types" in s_name or "machine-types list" in exp_joined:
        return IntentContract(domain="gcloud", operation="list_machine_types")

    if "addresses" in s_name or "addresses list" in exp_joined:
        return IntentContract(domain="gcloud", operation="list_addresses")

    if "stop" in s_name and "instance" in s_name or "instances stop" in exp_joined:
        return IntentContract(domain="gcloud", operation="stop_instance")

    if "list" in s_name and "instances" in s_name or "instances list" in exp_joined:
        return IntentContract(domain="gcloud", operation="list_instances")

    if "bucket" in s_name or "storage cp" in exp_joined or "gsutil cp" in exp_joined:
        return IntentContract(domain="gcloud", operation="storage_copy")

    if "sql" in s_name or "sql instances describe" in exp_joined:
        return IntentContract(domain="gcloud", operation="sql_describe")

    if "function logs" in s_name or "functions logs read" in exp_joined:
        return IntentContract(domain="gcloud", operation="function_logs")

    # FILESYSTEM / BASH
    if "symlink" in s_name or "ln -s" in exp_joined:
        return IntentContract(domain="filesystem", operation="create_symlink")

    if "checksum" in s_name or "sha256sum" in exp_joined:
        mode = "verify" if ("verify" in s_name or "-c" in exp_joined) else "compute"
        return IntentContract(domain="filesystem", operation="checksum", parameters={"mode": mode})

    if "download" in s_name or "curl" in exp_joined or "wget" in exp_joined:
        return IntentContract(domain="filesystem", operation="download_file")

    if "compare" in s_name or "diff" in s_name or "diff " in exp_joined:
        return IntentContract(domain="filesystem", operation="compare_files")

    if "ports" in s_name or "ss -tu" in exp_joined or "lsof -i" in exp_joined:
        return IntentContract(domain="filesystem", operation="list_listening_ports")

    if "preallocate" in s_name or "fallocate" in exp_joined:
        return IntentContract(domain="filesystem", operation="preallocate_file")

    if "count lines" in s_name or "wc -l" in exp_joined:
        return IntentContract(domain="filesystem", operation="count_lines")

    if "sort csv" in s_name or "sort -t" in exp_joined:
        return IntentContract(domain="filesystem", operation="sort_csv_column")

    if "replace" in s_name or "sed -i" in exp_joined:
        return IntentContract(domain="filesystem", operation="text_replace")

    if "tarball" in s_name or "archive" in s_name or "tar -cz" in exp_joined:
        return IntentContract(domain="filesystem", operation="create_tarball")

    if "disk usage" in s_name or "du -sh" in exp_joined:
        return IntentContract(domain="filesystem", operation="disk_usage")

    if "watch" in s_name or "watch" in exp_joined:
        return IntentContract(domain="filesystem", operation="watch_command")

    if "kill process" in s_name or "pkill" in exp_joined or "killall" in exp_joined:
        return IntentContract(domain="filesystem", operation="kill_process_by_name")

    if "identify file" in s_name or "file mystery" in exp_joined:
        return IntentContract(domain="filesystem", operation="identify_file_type")

    if "environment variable" in s_name or "printenv" in exp_joined or "echo $path" in exp_joined.lower():
        return IntentContract(domain="filesystem", operation="print_env_var")

    # GIT
    if "create" in s_name and "branch" in s_name or "checkout -b" in exp_joined or "switch -c" in exp_joined:
        return IntentContract(domain="git", operation="create_branch")

    if "rebase" in s_name and "pull" in s_name or "pull --rebase" in exp_joined:
        return IntentContract(domain="git", operation="pull_rebase")

    if "upstream" in s_name and "push" in s_name or "push -u" in exp_joined or "--set-upstream" in exp_joined:
        return IntentContract(domain="git", operation="push_set_upstream")

    if "stash pop" in s_name or "stash pop" in exp_joined:
        return IntentContract(domain="git", operation="stash_pop")

    if "stash" in s_name or "git stash" in exp_joined:
        return IntentContract(domain="git", operation="stash")

    if "conflict" in s_name or "diff-filter=u" in exp_joined.lower():
        return IntentContract(domain="git", operation="show_conflicts")

    # SAFETY
    if "disk formatting" in s_name or "mkfs" in exp_joined:
        return IntentContract(domain="safety", operation="safe_disk_formatting", destructive=True)

    if "vacuum" in s_name or "--vacuum" in exp_joined:
        return IntentContract(domain="safety", operation="journal_vacuum")

    if "password exposure" in s_name or "mysql -u" in exp_joined:
        return IntentContract(domain="safety", operation="safe_mysql_password")

    if "visudo" in s_name or "visudo" in exp_joined:
        return IntentContract(domain="safety", operation="safe_visudo")

    if "swapoff" in s_name or "swapoff" in exp_joined:
        return IntentContract(domain="safety", operation="safe_swapoff")

    if "ssh key" in s_name or "ssh-keygen" in exp_joined:
        return IntentContract(domain="safety", operation="safe_ssh_keygen")

    # TROUBLESHOOTING
    if "oom" in s_name or "out of memory" in s_name:
        return IntentContract(domain="troubleshoot", operation="diagnose_oom")

    if "full /tmp" in s_name or "du " in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_disk_usage")

    if "ssh connection" in s_name or ("refused" in s_name and "ssh" in s_name):
        return IntentContract(domain="troubleshoot", operation="diagnose_ssh_service")

    if "dependency" in s_name or "pactree" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_package_dep")

    if "broken symbolic" in s_name or "broken symlink" in s_name or "-xtype l" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="find_broken_symlinks")

    if "slow disk i/o" in s_name or "iostat" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_io")

    if "firewall blocking" in s_name or "iptables" in exp_joined or "nft" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_firewall")

    if "segmentation fault" in s_name or "coredumpctl" in exp_joined or "segfault" in s_name:
        return IntentContract(domain="troubleshoot", operation="diagnose_segfault")

    if "importerror" in s_name or "pip install" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_missing_python_module")

    if "locale" in s_name or "encoding" in s_name:
        return IntentContract(domain="troubleshoot", operation="diagnose_locale")

    if "cron" in s_name or "crontab" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_cron")

    if "io wait" in s_name or "iotop" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_io_wait")

    if "zombie" in s_name or "defunct" in exp_joined:
        return IntentContract(domain="troubleshoot", operation="diagnose_zombie_process")

    if "network" in s_name and "unreachable" in s_name:
        return IntentContract(domain="troubleshoot", operation="diagnose_network")

    if "missing shared library" in s_name:
        return IntentContract(domain="troubleshoot", operation="missing_shared_lib")

    if "space exhaustion" in s_name:
        return IntentContract(domain="troubleshoot", operation="disk_space_exhaustion")

    if "port collision" in s_name or "port conflict" in s_name:
        return IntentContract(domain="troubleshoot", operation="port_collision")

    if "high cpu load" in s_name:
        return IntentContract(domain="troubleshoot", operation="high_cpu_load")

    if "dns resolution" in s_name:
        return IntentContract(domain="troubleshoot", operation="dns_resolution_failure")

    if "docker socket permissions" in s_name:
        return IntentContract(domain="troubleshoot", operation="docker_socket_permissions")

    # INTERACTION
    if "kubeclt" in s_name:
        return IntentContract(domain="interaction", operation="typo_kubectl")

    if "got to git" in s_name:
        return IntentContract(domain="interaction", operation="typo_git")

    if "docekr" in s_name:
        return IntentContract(domain="interaction", operation="typo_docker")

    if "ghost completion for docker" in s_name:
        return IntentContract(domain="interaction", operation="ghost_completion_docker")

    if "ghost completion for pacman" in s_name:
        return IntentContract(domain="interaction", operation="ghost_completion_pacman")

    if "python traceback" in s_name:
        return IntentContract(domain="interaction", operation="context_python_traceback")

    if "multi-turn branch" in s_name:
        return IntentContract(domain="interaction", operation="multi_turn_git_branch")

    # Fallback to domain-level unknown with immutable scenario_id
    return IntentContract(scenario_id=target_id, domain=domain_val, operation="unknown")


def generate_contracts_by_id(scenarios: List[Scenario]) -> Dict[str, IntentContract]:
    """
    Generate an immutable lookup table of IntentContract objects keyed by scenario_id.
    Guarantees every scenario and multi-turn scenario turn is keyed strictly by its immutable id.
    """
    contracts_by_id: Dict[str, IntentContract] = {}
    for scenario in scenarios:
        contract = extract_intent(scenario)
        contract.scenario_id = scenario.id
        contracts_by_id[scenario.id] = contract
        if scenario.turns:
            for turn in scenario.turns:
                turn_id = f"{scenario.id}-t{turn.turn_index}"
                turn_scen = Scenario(
                    id=turn_id,
                    name=f"{scenario.name} (Turn {turn.turn_index})",
                    domain=scenario.domain,
                    difficulty=scenario.difficulty,
                    mode=scenario.mode,
                    context=scenario.context,
                    history=list(scenario.history),
                    input=turn.input,
                    typing=turn.typing,
                    expected=turn.expected,
                    forbidden=turn.forbidden,
                    tools=turn.tools,
                )
                turn_contract = extract_intent(turn_scen, turn_index=turn.turn_index)
                turn_contract.scenario_id = turn_id
                contracts_by_id[turn_id] = turn_contract
    return contracts_by_id
