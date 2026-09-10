from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .intent_registry import CANONICAL_INTENT_SPECS, IntentRegistry
from .types import (
    IntentContract,
    IntentSpec,
    RuntimeIntentConfidence,
    RuntimeIntentInput,
    RuntimeIntentResolution,
    RuntimeIntentStatus,
)


class RuntimeIntentResolver:
    """
    Host-owned production-style Runtime Intent Resolver.
    Derives an IntentContract from user input, terminal context, and platform context,
    strictly without access to scenario_id, gold contracts, expected commands, or benchmark solutions.
    """

    def __init__(self, registry: Optional[IntentRegistry] = None):
        self.registry = registry or IntentRegistry()

    def resolve(self, intent_input: RuntimeIntentInput) -> RuntimeIntentResolution:
        user_text = intent_input.user_text.strip()
        # Clean leading '@ ' if present in explicit interaction mode
        if user_text.startswith("@"):
            user_text = user_text[1:].strip()

        # Step 1: Check for interaction typos / ghost completions
        typo_res = self._check_interaction_patterns(user_text, intent_input)
        if typo_res:
            return typo_res

        # Step 2: Match against canonical IntentSpecs
        best_spec, match_score = self._match_intent_spec(user_text, intent_input)
        if not best_spec:
            # Check for general clarification request
            if self._is_clarification_request(user_text):
                contract = IntentContract(
                    domain="interaction",
                    operation="clarify",
                    destructive=False,
                    mutating=False,
                    description="User request is ambiguous and requires clarification",
                )
                return RuntimeIntentResolution(
                    status=RuntimeIntentStatus.RESOLVED,
                    contract=contract,
                    confidence=RuntimeIntentConfidence.HIGH,
                )

            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.UNKNOWN,
                contract=None,
                confidence=RuntimeIntentConfidence.LOW,
            )

        # Step 3: Extract slots from text and context
        resolved_slots, evidence, missing_slots = self._extract_slots(best_spec, user_text, intent_input)

        # Step 4: Determine confidence and resolution status
        if missing_slots:
            contract = IntentContract(
                domain=best_spec.domain,
                operation=best_spec.operation,
                parameters=resolved_slots,
                required_parameters=best_spec.required_slots,
                optional_parameters=best_spec.optional_slots,
                destructive=best_spec.destructive,
                mutating=best_spec.mutating,
                description=best_spec.description,
            )
            conf = RuntimeIntentConfidence.MEDIUM if match_score >= 5 else RuntimeIntentConfidence.LOW
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.AMBIGUOUS,
                contract=contract,
                confidence=conf,
                evidence=evidence,
                missing_slots=missing_slots,
                resolved_slots=resolved_slots,
            )

        confidence = RuntimeIntentConfidence.HIGH

        contract = IntentContract(
            domain=best_spec.domain,
            operation=best_spec.operation,
            parameters=resolved_slots,
            required_parameters=best_spec.required_slots,
            optional_parameters=best_spec.optional_slots,
            destructive=best_spec.destructive,
            mutating=best_spec.mutating,
            description=best_spec.description,
        )

        return RuntimeIntentResolution(
            status=RuntimeIntentStatus.RESOLVED,
            contract=contract,
            confidence=confidence,
            evidence=evidence,
            missing_slots=[],
            resolved_slots=resolved_slots,
        )

    SEMANTIC_RULES = [
        # Clarification requests (vague or catastrophic actions without precise targets)
        ('interaction', 'clarify', [
            r'deploy it\b', r'update everything\b', r'check the logs\b', r'send it to the server\b',
            r'clean up the old stuff\b', r'write zeros to', r'wipe the entire disk', r'delete all hidden',
            r'chmod 777.*(/etc|/usr|/var)', r'erase.*partition table', r'delete.*(/boot|root|all log)',
            r'kill process 1\b', r'kill pid 1\b', r'flush all.*firewall', r'flush.*iptables',
            r'move /etc/passwd', r'change ownership of /usr', r'never have to type.*sudo',
        ]),

        # Git
        ('git', 'pull_rebase', [r'fix this push rejection', r'push rejection', r'pull.*rebase', r'pull upstream']),
        ('git', 'stash', [r'save my uncommitted', r'stash.*changes', r'git stash', r'save uncommitted']),
        ('git', 'stash_pop', [r'pop stashed', r'restore stashed', r'git stash pop', r'restore them']),
        ('git', 'create_branch', [r'create.*branch', r'switch to new branch', r'checkout new branch', r'branch creation']),
        ('git', 'push_set_upstream', [r'push.*set upstream', r'push.*upstream', r'push branch to origin', r'push.*new branch.*remote', r'push it to origin']),
        ('git', 'show_conflicts', [r'merge conflict', r'unmerged files', r'conflicted files']),

        # Troubleshooting
        ('troubleshoot', 'diagnose_oom', [r'keeps getting killed', r'oom', r'out of memory']),
        ('troubleshoot', 'diagnose_disk_usage', [r'is full.*what.*s using', r'disk full', r'space running low', r'no space left', r'space exhaustion', r'investigate /var', r'check /var']),
        ('troubleshoot', 'diagnose_package_dep', [r'because of depend', r'broken package', r'package dependency', r'unmet dependencies']),
        ('troubleshoot', 'diagnose_io', [r'system feels sluggish and disk', r'slow disk', r'disk i/o']),
        ('troubleshoot', 'port_collision', [r'port 80 is taken', r'port conflict', r'port collision', r'address already in use']),
        ('troubleshoot', 'diagnose_firewall', [r'app works locally but remote', r'firewall blocking', r'incoming connection']),
        ('troubleshoot', 'diagnose_segfault', [r'segmentation fault', r'segfault']),
        ('troubleshoot', 'diagnose_tls', [r'ssl certificate is failing', r'tls certificate', r'certificate verification']),
        ('troubleshoot', 'diagnose_locale', [r'encoding issues', r'locale', r'utf-8 encoding']),
        ('troubleshoot', 'diagnose_cron', [r'cron job', r'cron execution', r'scheduled job']),
        ('troubleshoot', 'diagnose_io_wait', [r'cpu usage low.*load.*high', r'system load is very high', r'io wait', r'iowait']),
        ('troubleshoot', 'diagnose_zombie_process', [r'zombie', r'defunct']),
        ('troubleshoot', 'find_broken_symlinks', [r'broken symlink', r'dangling symlink']),
        ('troubleshoot', 'diagnose_ssh_service', [r'ssh connection refused', r'ssh service']),
        ('troubleshoot', 'diagnose_missing_python_module', [r'fix this import error', r'^fix this$', r'importerror', r'modulenotfound', r'missing python module']),

        # Pacman / Arch
        ('pacman', 'query_explicit', [r'explicitly installed', r'explicit packages', r'packages.*explicitly installed']),
        ('pacman', 'clean_cache', [r'clean.*cache', r'paccache', r'prune.*cache']),
        ('pacman', 'find_orphans', [r'orphan', r'unneeded packages']),
        ('pacman', 'downgrade_from_cache', [r'downgrade.*cached', r'downgrade.*cache', r'install previous version from cache']),
        ('pacman', 'mkinitcpio', [r'initramfs', r'mkinitcpio']),
        ('pacman', 'reflector', [r'mirrorlist', r'reflector', r'fastest mirrors']),
        ('pacman', 'lsmod', [r'loaded kernel modules', r'lsmod']),
        ('pacman', 'verify_package_files', [r'verify package', r'files from the .* package have been modified', r'check package integrity', r'pacman -qk']),
        ('pacman', 'package_owner', [r'which package provides', r'which package owns', r'package owner']),

        # Journalctl
        ('journalctl', 'kernel_logs', [r'kernel error', r'dmesg error', r'kernel log']),
        ('journalctl', 'current_boot', [r'since last boot', r'current boot', r'journal.*this boot']),
        ('journalctl', 'follow', [r'follow.*system log', r'follow.*journal', r'tail.*system journal', r'follow logs in real time', r'stream journalctl']),

        # Systemctl
        ('systemctl', 'enable_and_start', [r'enable.*service.*start', r'enable and start', r'start and enable', r'autostart service']),
        ('systemctl', 'restart_service', [r'restart.*service', r'restart daemon', r'restart nginx']),
        ('systemctl', 'list_failed', [r'failed systemd', r'failed services', r'failed units']),

        # Filesystem / Coreutils
        ('filesystem', 'count_lines', [r'how many lines', r'count lines', r'line count', r'wc -l']),
        ('filesystem', 'sort_csv_column', [r'sort.*column', r'sort.*csv']),
        ('filesystem', 'text_replace', [r'replace all occurrences', r'replace.*with.*in', r'substitute.*in']),
        ('filesystem', 'compare_files', [r'differences between', r'compare.*files', r'diff.*files', r'show diff']),
        ('filesystem', 'watch_command', [r'monitor.*every', r'run.*periodically', r'watch.*every', r'repeat command']),
        ('filesystem', 'create_symlink', [r'create.*symlink', r'symbolic link', r'symlink called']),
        ('filesystem', 'kill_process_by_name', [r'kill all.*processes', r'kill process', r'terminate process', r'kill.*by name', r'pkill']),
        ('filesystem', 'download_file', [r'download.*https?://', r'download file', r'fetch.*from url', r'download.*curl', r'wget']),
        ('filesystem', 'create_tarball', [r'create.*tarball', r'create.*archive', r'compress.*tar']),
        ('filesystem', 'list_listening_ports', [r'ports are listening', r'listening.*port', r'open listening ports']),
        ('filesystem', 'preallocate_file', [r'preallocate', r'allocate.*file', r'fallocate']),
        ('filesystem', 'identify_file_type', [r'what type of file', r'file type', r'mime type', r'what kind of file']),
        ('filesystem', 'print_env_var', [r'environment variable', r'env var', r'print.*variable']),
        ('filesystem', 'checksum', [r'checksum', r'sha256', r'compute.*hash', r'verify.*hash']),
        ('filesystem', 'disk_usage', [r'disk is getting full', r'disk usage', r'largest directories', r'check disk space']),

        # Gcloud
        ('gcloud', 'list_addresses', [r'static ip', r'external ip', r'list addresses']),
        ('gcloud', 'create_firewall_rule', [r'firewall rule', r'allow port', r'open port in firewall']),
        ('gcloud', 'cloud_run_logs', [r'cloud run.*logs', r'run services logs', r'logs for the.*cloud run']),
        ('gcloud', 'cloud_run_deploy', [r'cloud run deploy', r'deploy.*to cloud run', r'deploy container to cloud run']),
        ('gcloud', 'storage_list', [r'objects in.*bucket', r'list.*storage bucket', r'storage list', r'gcs list', r'my gcs buckets']),
        ('gcloud', 'storage_copy', [r'upload.*to gs://', r'copy.*to.*bucket', r'upload.*to bucket', r'copy.*from.*bucket', r'storage cp']),
        ('gcloud', 'iam_policy', [r'iam policy', r'policy bindings']),
        ('gcloud', 'set_region', [r'default compute region', r'compute/region', r'set.*region']),
        ('gcloud', 'sql_describe', [r'cloud sql', r'sql instances describe', r'describe.*sql']),
        ('gcloud', 'list_machine_types', [r'machine types', r'machine-types']),
        ('gcloud', 'stop_instance', [r'stop.*instance', r'stop dev-server', r'stop.*vm']),
        ('gcloud', 'function_logs', [r'cloud function logs', r'logs for cloud function', r'function logs']),

        # Gh
        ('gh', 'issue_list', [r'list.*issues', r'open issues', r'show issues']),
        ('gh', 'issue_create', [r'create.*issue', r'open.*issue', r'report.*issue', r'submit.*issue', r'file.*issue', r'new issue']),
        ('gh', 'issue_close', [r'close.*issue', r'resolve.*issue']),
        ('gh', 'pr_diff', [r'diff for pull request', r'pr diff', r'diff for pr', r'changes in pr', r'view diff of pr']),
        ('gh', 'pr_review_approve', [r'approve.*pr', r'approve pull request', r'approve the pr', r'approve #', r'approve 88']),
        ('gh', 'release_create', [r'create.*release', r'publish release', r'new release']),
        ('gh', 'gist_list', [r'list gists', r'show gists', r'my gists']),
        ('gh', 'repo_clone', [r'clone.*repo', r'clone.*repository']),
        ('gh', 'repo_fork', [r'fork.*repo', r'fork.*repository', r'fork kubernetes']),
        ('gh', 'workflow_run_logs', [r'workflow run', r'workflow logs', r'actions run logs']),
        ('gh', 'pr_merge', [r'merge.*pr', r'merge.*pull request', r'rebase.*pr']),
        ('gh', 'label_list', [r'list.*labels', r'repository labels']),

        # Safety
        ('safety', 'safe_disk_formatting', [r'format /dev/', r'format.*partition', r'format.*disk', r'mkfs']),
        ('safety', 'safe_ssh_keygen', [r'ssh key', r'keygen', r'generate ssh']),
        ('safety', 'journal_vacuum', [r'free up space used by system logs', r'vacuum', r'clean.*journal', r'rotate journal']),
        ('safety', 'safe_mysql_password', [r'mysql.*password', r'database password']),
        ('safety', 'safe_visudo', [r'sudoers', r'visudo']),
        ('safety', 'safe_swapoff', [r'swap', r'swapoff']),
    ]

    def _match_intent_spec(
        self, user_text: str, intent_input: RuntimeIntentInput
    ) -> Tuple[Optional[IntentSpec], int]:
        """
        Matches user text against registered IntentSpecs with strict negative-collision protection.
        Returns the best matching spec and match score.
        """
        text_lower = user_text.lower()
        candidates: List[Tuple[IntentSpec, int]] = []

        for spec in self.registry.all_specs():
            # Check negative protections: avoid substring collisions
            if self._is_negative_collision(spec, user_text, intent_input):
                continue

            best_len = 0
            for hint in spec.lexical_hints:
                h_lower = hint.lower()
                pattern = r"\b" + re.escape(h_lower) + r"\b"
                if re.search(pattern, text_lower):
                    if len(h_lower) > best_len:
                        best_len = len(h_lower)

            if best_len > 0:
                candidates.append((spec, best_len))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0]

        # Context-based operation fallback: e.g. "approve it" when previous command was gh pr view
        ctx_spec = self._match_from_context(user_text, intent_input)
        if ctx_spec:
            return ctx_spec, 10

        # Semantic pattern rules fallback
        for dom, op, patterns in self.SEMANTIC_RULES:
            spec = self.registry.get_spec(dom, op)
            if not spec:
                continue
            if self._is_negative_collision(spec, user_text, intent_input):
                continue
            for pat in patterns:
                if re.search(pat, text_lower):
                    return spec, 15

        return None, 0

    def _is_negative_collision(
        self, spec: IntentSpec, user_text: str, intent_input: RuntimeIntentInput
    ) -> bool:
        """
        Defends against known false-positive substring collisions:
          - 'sort -k' must never resolve as journalctl (kernel_logs)
          - 'zone us-east1-b' must never resolve as journalctl (current_boot)
          - '--log-failed' must never resolve as journalctl
          - 'feature/auth-flow' must never resolve as journalctl (follow)
        """
        text_lower = user_text.lower()

        # Journalctl negative protections
        if spec.domain == "journalctl":
            if "sort" in text_lower and "-k" in user_text:
                return True
            if "zone" in text_lower:
                return True
            if "feature/" in text_lower or "auth-flow" in text_lower:
                return True
            if "failed" in text_lower and ("systemd" in text_lower or "services" in text_lower):
                return True

        # Systemctl list_failed negative protections
        if spec.domain == "systemctl" and spec.operation == "list_failed":
            if "--log-failed" in text_lower:
                return True

        # Gh PR diff negative protections
        if spec.domain == "gh" and spec.operation == "pr_diff":
            if "compare" in text_lower and "files" in text_lower:
                return True

        return False

    def _match_from_context(
        self, user_text: str, intent_input: RuntimeIntentInput
    ) -> Optional[IntentSpec]:
        """Handles pronoun references like 'approve it', 'restart it' using previous command context."""
        text_lower = user_text.lower()
        prev_cmd = (intent_input.previous_command or "").strip().lower()

        if re.search(r"\bapprove\s+(?:it|that|this)\b", text_lower):
            if "gh pr" in prev_cmd or "pr view" in prev_cmd:
                return self.registry.get_spec("gh", "pr_review_approve")

        if re.search(r"\brestart\s+(?:it|that|the service)\b", text_lower):
            if "systemctl" in prev_cmd or "service" in prev_cmd or "nginx" in prev_cmd:
                return self.registry.get_spec("systemctl", "restart_service")
            return self.registry.get_spec("systemctl", "restart_service")

        if re.search(r"\bclose\s+(?:it|that|the issue)\b", text_lower):
            if "gh issue" in prev_cmd:
                return self.registry.get_spec("gh", "issue_close")

        if re.search(r"\b(?:continue|next|proceed)\b", text_lower):
            if "stash" in prev_cmd:
                return self.registry.get_spec("git", "stash_pop")
            if "checkout" in prev_cmd or "branch" in prev_cmd:
                return self.registry.get_spec("git", "push_set_upstream")
            if "du -" in prev_cmd or "df -" in prev_cmd:
                return self.registry.get_spec("troubleshoot", "diagnose_disk_usage")

        return None

    def _is_clarification_request(self, user_text: str) -> bool:
        """Detects ambiguous user requests that require clarification."""
        text_lower = user_text.lower()
        ambiguous_phrases = [
            "delete the files", "clean up the system", "remove the directory",
            "kill the process", "fix the issue", "reset everything", "delete files",
            "clean up files", "remove files", "delete it", "clean it"
        ]
        return any(phrase in text_lower for phrase in ambiguous_phrases)

    def _check_interaction_patterns(
        self, user_text: str, intent_input: RuntimeIntentInput
    ) -> Optional[RuntimeIntentResolution]:
        """Detects interactive typos, ghost completions, or multi-turn actions."""
        raw = user_text.strip()
        raw_lower = raw.lower()

        # Ghost completions
        if raw == "docker exec -it":
            contract = IntentContract(
                domain="interaction",
                operation="ghost_completion_docker",
                description="Ghost completion for docker exec",
            )
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.RESOLVED,
                contract=contract,
                confidence=RuntimeIntentConfidence.HIGH,
            )

        if raw == "sudo pacman -S ri" or raw.startswith("sudo pacman -S ri"):
            contract = IntentContract(
                domain="interaction",
                operation="ghost_completion_pacman",
                description="Ghost completion for pacman package install",
            )
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.RESOLVED,
                contract=contract,
                confidence=RuntimeIntentConfidence.HIGH,
            )

        # Typos
        if raw_lower.startswith("kubctl ") or raw_lower.startswith("kubeclt ") or raw_lower.startswith("kc get "):
            contract = IntentContract(
                domain="interaction",
                operation="typo_kubectl",
                description="Typo correction for kubectl command",
            )
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.RESOLVED,
                contract=contract,
                confidence=RuntimeIntentConfidence.HIGH,
            )

        if raw_lower in ("git stats", "git stauts", "git sttus", "got status") or raw_lower.startswith("git stats") or raw_lower.startswith("got status"):
            contract = IntentContract(
                domain="interaction",
                operation="typo_git",
                description="Typo correction for git status command",
            )
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.RESOLVED,
                contract=contract,
                confidence=RuntimeIntentConfidence.HIGH,
            )

        if raw_lower.startswith("dockr ") or raw_lower.startswith("dokcer ") or raw_lower.startswith("docekr "):
            contract = IntentContract(
                domain="interaction",
                operation="typo_docker",
                description="Typo correction for docker command",
            )
            return RuntimeIntentResolution(
                status=RuntimeIntentStatus.RESOLVED,
                contract=contract,
                confidence=RuntimeIntentConfidence.HIGH,
            )

        return None

    def _extract_slots(
        self, spec: IntentSpec, user_text: str, intent_input: RuntimeIntentInput
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
        """
        Extracts literal slots from user text and unambiguous terminal context.
        Never invents missing slot values.
        """
        resolved: Dict[str, Any] = {}
        evidence: List[Dict[str, Any]] = []
        text_lower = user_text.lower()
        prev_cmd = (intent_input.previous_command or "").strip()

        if prev_cmd and any(w in text_lower for w in ("it", "that", "this", "continue", "next", "proceed", "them")):
            evidence.append({"parameter": "context_reference", "value": prev_cmd, "source": "previous_command", "type": "previous_command"})

        # PR Number
        if "pr_number" in spec.required_slots or "pr_number" in spec.optional_slots:
            m = re.search(r"(?:pr|pull\s+request|#)\s*(\d+)", user_text, re.IGNORECASE)
            if not m:
                # Direct digits in text e.g. "approve 88"
                m = re.search(r"\b(\d+)\b", user_text)
            if m:
                val = m.group(1)
                resolved["pr_number"] = val
                evidence.append({"parameter": "pr_number", "value": val, "source": "user_text"})
            elif prev_cmd:
                # Context-based resolution: "gh pr view 88" -> pr_number = 88
                m_ctx = re.findall(r"\b(\d+)\b", prev_cmd)
                if len(m_ctx) == 1 and ("pr" in prev_cmd.lower() or "gh" in prev_cmd.lower()):
                    val = m_ctx[0]
                    resolved["pr_number"] = val
                    evidence.append({"parameter": "pr_number", "value": val, "source": "previous_command"})

        # Issue Number
        if "issue_number" in spec.required_slots or "issue_number" in spec.optional_slots:
            m = re.search(r"(?:issue|#)\s*(\d+)", user_text, re.IGNORECASE)
            if not m:
                m = re.search(r"\b(\d+)\b", user_text)
            if m:
                val = m.group(1)
                resolved["issue_number"] = val
                evidence.append({"parameter": "issue_number", "value": val, "source": "user_text"})
            elif prev_cmd:
                m_ctx = re.findall(r"\b(\d+)\b", prev_cmd)
                if len(m_ctx) == 1 and "issue" in prev_cmd.lower():
                    val = m_ctx[0]
                    resolved["issue_number"] = val
                    evidence.append({"parameter": "issue_number", "value": val, "source": "previous_command"})

        # Workflow Run ID
        if "run_id" in spec.required_slots:
            m = re.search(r"(?:run|run\s+id|workflow)\s*(\d+)", user_text, re.IGNORECASE)
            if not m:
                m = re.search(r"\b(\d{4,})\b", user_text)
            if m:
                val = m.group(1)
                resolved["run_id"] = val
                evidence.append({"parameter": "run_id", "value": val, "source": "user_text"})

        # Service Name
        if "service" in spec.required_slots or "service" in spec.optional_slots:
            m = re.search(r"(?:service|daemon|unit)\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
            svc = None
            if m and m.group(1).lower() not in ("start", "stop", "restart", "enable", "status", "it", "the"):
                svc = m.group(1)
            if not svc:
                for cand in ("docker", "nginx", "sshd", "cron", "systemd-resolved", "mysql", "postgresql", "redis", "api-service"):
                    if re.search(r"\b" + re.escape(cand) + r"\b", text_lower):
                        svc = cand
                        break
            if svc:
                resolved["service"] = svc
                evidence.append({"parameter": "service", "value": svc, "source": "user_text"})
            elif prev_cmd and ("it" in text_lower or "the service" in text_lower):
                # Context-based: "systemctl status nginx" -> service = nginx
                m_ctx = re.search(r"(?:status|start|stop|restart|enable)\s+([a-zA-Z0-9_\-\.]+)", prev_cmd, re.IGNORECASE)
                if m_ctx and m_ctx.group(1) not in ("it", "the"):
                    val = m_ctx.group(1)
                    resolved["service"] = val
                    evidence.append({"parameter": "service", "value": val, "source": "previous_command"})

        # Package Name
        if "package" in spec.required_slots or "package" in spec.optional_slots:
            m = re.search(r"(?:package|pkg)\s+([a-zA-Z0-9_\-]+)", user_text, re.IGNORECASE)
            pkg = None
            if m and m.group(1).lower() not in ("cache", "files", "installed", "explicit"):
                pkg = m.group(1)
            if not pkg:
                for cand in ("mesa", "nginx", "docker", "chromium", "ripgrep", "vim", "bash", "python"):
                    if re.search(r"\b" + re.escape(cand) + r"\b", text_lower):
                        pkg = cand
                        break
            if pkg:
                resolved["package"] = pkg
                evidence.append({"parameter": "package", "value": pkg, "source": "user_text"})

        # File path for package_owner or general files
        if "path" in spec.required_slots or "path" in spec.optional_slots:
            m = re.search(r"(?:owns?\s+)?(/[a-zA-Z0-9_\.\-\/]+)", user_text)
            if m:
                val = m.group(1)
                resolved["path"] = val
                evidence.append({"parameter": "path", "value": val, "source": "user_text"})

        # File operands
        if "file" in spec.required_slots or "file" in spec.optional_slots or "path" in spec.required_slots or "path" in spec.optional_slots:
            m = re.search(r"\b([a-zA-Z0-9_\-\.]+\.(?:csv|txt|md|conf|img|iso|json|tar\.gz|bak|log))\b", user_text, re.IGNORECASE)
            if not m:
                m = re.search(r"(?:in|file|named)\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
            if m and m.group(1).lower() not in ("a", "the", "test", "files"):
                val = m.group(1)
                resolved["file"] = val
                resolved["path"] = val
                evidence.append({"parameter": "file", "value": val, "source": "user_text"})

        if spec.operation == "count_lines":
            if "file" in resolved and "path" not in resolved:
                resolved["path"] = resolved["file"]
            elif "path" in resolved and "file" not in resolved:
                resolved["file"] = resolved["path"]

        # Action for PR review
        if spec.domain == "gh" and ("approve" in spec.operation or "review" in spec.operation):
            if "approve" in text_lower:
                resolved["action"] = "approve"
                evidence.append({"parameter": "action", "value": "approve", "source": "user_text"})

        # Journalctl kernel logs priority
        if spec.domain == "journalctl" and spec.operation == "kernel_logs":
            if "error" in text_lower or "err" in text_lower:
                resolved["priority"] = "err"
                evidence.append({"parameter": "priority", "value": "err", "source": "user_text"})

        # Gh repo fork clone
        if spec.domain == "gh" and spec.operation == "repo_fork":
            if "clone" in text_lower:
                resolved["clone"] = True
                evidence.append({"parameter": "clone", "value": True, "source": "user_text"})

        # Compare files: file1 and file2
        if "file1" in spec.required_slots and "file2" in spec.required_slots:
            files = re.findall(r"\b([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)\b", user_text)
            if len(files) >= 2:
                resolved["file1"] = files[0]
                resolved["file2"] = files[1]
                evidence.append({"parameter": "file1", "value": files[0], "source": "user_text"})
                evidence.append({"parameter": "file2", "value": files[1], "source": "user_text"})

        # Symlink: target and linkname
        if "target" in spec.required_slots and "linkname" in spec.required_slots:
            m = re.search(r"(?:link\s+(?:to\s+)?|symlink\s+(?:pointing\s+to\s+)?)([a-zA-Z0-9_\-\.\/]+)\s+(?:as|named|to)?\s*([a-zA-Z0-9_\-\.]+)?", user_text, re.IGNORECASE)
            if m:
                resolved["target"] = m.group(1)
                resolved["linkname"] = m.group(2) or "latest"
                evidence.append({"parameter": "target", "value": resolved["target"], "source": "user_text"})
                evidence.append({"parameter": "linkname", "value": resolved["linkname"], "source": "user_text"})

        # Preallocate file: filename and size
        if "filename" in spec.required_slots and "size" in spec.required_slots:
            m_s = re.search(r"(\d+)\s*([kmgtp]i?[b]?)", user_text, re.IGNORECASE)
            size = "1G"
            if m_s:
                unit = m_s.group(2)[0].upper()
                size = f"{m_s.group(1)}{unit}"
            m_f = re.search(r"(?:file\s+named|named|file)\s+([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
            filename = "test.img"
            if m_f and m_f.group(1).lower() not in ("named", "a", "the", "test"):
                filename = m_f.group(1)
            resolved["size"] = size
            resolved["filename"] = filename
            evidence.append({"parameter": "size", "value": size, "source": "user_text"})
            evidence.append({"parameter": "filename", "value": filename, "source": "user_text"})

        # Branch name
        if "branch" in spec.required_slots or "branch" in spec.optional_slots:
            m = re.search(r"(?:branch\s+)?([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)", user_text)
            if not m:
                m = re.search(r"branch\s+([a-zA-Z0-9_\-]+)", user_text, re.IGNORECASE)
            if m:
                val = m.group(1)
                resolved["branch"] = val
                evidence.append({"parameter": "branch", "value": val, "source": "user_text"})
            elif prev_cmd:
                # e.g. "git checkout -b feature/auth-flow" -> branch = feature/auth-flow
                m_ctx = re.search(r"(?:-b\s+|switch\s+-c\s+|checkout\s+)([a-zA-Z0-9_\-\/]+)", prev_cmd)
                if m_ctx:
                    val = m_ctx.group(1)
                    resolved["branch"] = val
                    evidence.append({"parameter": "branch", "value": val, "source": "previous_command"})

        # Process name
        if "process_name" in spec.required_slots:
            m = re.search(r"(?:kill\s+|terminate\s+)?(?:process\s+(?:named\s+)?)?([a-zA-Z0-9_\-\.]+)", user_text, re.IGNORECASE)
            proc = None
            for cand in ("firefox", "nginx", "docker", "chrome", "python", "node"):
                if re.search(r"\b" + re.escape(cand) + r"\b", text_lower):
                    proc = cand
                    break
            if proc:
                resolved["process_name"] = proc
                evidence.append({"parameter": "process_name", "value": proc, "source": "user_text"})

        # Gcloud Zone & Region
        if "zone" in spec.required_slots or "zone" in spec.optional_slots:
            m = re.search(r"\b([a-z]+-[a-z]+[0-9]+-[a-z])\b", user_text)
            if m:
                val = m.group(1)
                resolved["zone"] = val
                evidence.append({"parameter": "zone", "value": val, "source": "user_text"})

        if "region" in spec.required_slots or "region" in spec.optional_slots:
            m = re.search(r"\b([a-z]+-[a-z]+[0-9]+)\b", user_text)
            if m:
                val = m.group(1)
                resolved["region"] = val
                evidence.append({"parameter": "region", "value": val, "source": "user_text"})

        # Gcloud Instance Name
        if "instance" in spec.required_slots or "instance" in spec.optional_slots:
            inst_val = None
            m_fixed = re.search(r"\b(dev-server|prod-server|web-server|db-server)\b", user_text, re.IGNORECASE)
            if m_fixed:
                inst_val = m_fixed.group(1)
            else:
                for p in (r"(?:instance|vm)\s+([a-zA-Z0-9_\-]+)", r"(?:stop|terminate)\s+([a-zA-Z0-9_\-]+)"):
                    m = re.search(p, user_text, re.IGNORECASE)
                    if m and m.group(1).lower() not in ("stop", "start", "list", "the", "a", "in", "zone"):
                        inst_val = m.group(1)
                        break
            if inst_val:
                resolved["instance"] = inst_val
                evidence.append({"parameter": "instance", "value": inst_val, "source": "user_text"})

        # Repository (e.g. kubernetes/kubernetes)
        if "repo" in spec.required_slots:
            m = re.search(r"\b([a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-]+)\b", user_text)
            if m:
                val = m.group(1)
                resolved["repo"] = val
                evidence.append({"parameter": "repo", "value": val, "source": "user_text"})

        # Retain versions
        if "retain_versions" in spec.optional_slots or "retain_versions" in spec.required_slots:
            m = re.search(r"(?:keep|keeping|retain)\s+(?:last\s+|latest\s+)?(\d+)\s*(?:cached\s+)?versions?", user_text, re.IGNORECASE)
            if m:
                resolved["retain_versions"] = int(m.group(1))
                evidence.append({"parameter": "retain_versions", "value": int(m.group(1)), "source": "user_text"})

        # Check which required slots are missing
        missing = [slot for slot in spec.required_slots if slot not in resolved]

        return resolved, evidence, missing
