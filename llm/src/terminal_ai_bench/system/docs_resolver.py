from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .types import DocLookupResult, IntentValidationResult, ValidationResult


class DocumentationResolver:
    """
    Local Documentation Resolver for cAIman Terminal.
    Retrieves the minimal relevant documentation needed for repair from frozen fixtures.
    """

    def __init__(self, fixtures_dir: Path | str = "fixtures"):
        self.fixtures_dir = Path(fixtures_dir)

    def resolve(
        self,
        validation: Optional[ValidationResult] = None,
        intent_validation: Optional[IntentValidationResult] = None,
    ) -> DocLookupResult:
        """Resolve minimal targeted documentation for an invalid or uncertain command or semantic mismatch."""
        topic = None
        if intent_validation and intent_validation.help_topic:
            topic = intent_validation.help_topic
        elif validation and validation.help_topic:
            topic = validation.help_topic
        elif validation and validation.executable:
            topic = validation.executable
        elif intent_validation and intent_validation.domain:
            topic = intent_validation.domain

        if not topic:
            return DocLookupResult(performed=False)

        # 1. Search in fixtures
        exe = (validation.executable if validation else None) or topic.split()[0]
        subcmd = validation.subcommand if validation else []
        topic_parts = topic.split()
        sub_path = "-".join(topic_parts[1:]) if len(topic_parts) > 1 else ""

        fixture_candidates = [
            # Exact command help fixture (e.g. fixtures/gh/pr-review-help.txt)
            self.fixtures_dir / exe / f"{sub_path}-help.txt" if sub_path else None,
            self.fixtures_dir / exe / f"{'-'.join(subcmd)}-help.txt" if subcmd else None,
            self.fixtures_dir / "help" / f"{exe}.txt",
            self.fixtures_dir / "man" / f"{exe}.txt",
            self.fixtures_dir / exe / f"{exe}-help.txt",
            self.fixtures_dir / "man" / f"{topic}.txt",
            self.fixtures_dir / "help" / f"{topic}.txt",
        ]

        content = None
        source = None

        for candidate in fixture_candidates:
            if candidate and candidate.exists():
                raw = candidate.read_text(encoding="utf-8").strip()
                content = self._extract_minimal_snippet(raw, topic)
                source = str(candidate.relative_to(self.fixtures_dir.parent) if self.fixtures_dir.parent in candidate.parents else candidate)
                break

        # 2. Fallback to built-in structured micro-help if fixture file not present
        if not content:
            content, source = self._generate_builtin_snippet(topic, exe, validation, intent_validation)

        if content:
            return DocLookupResult(
                performed=True,
                provider=f"{exe}_help",
                topic=topic,
                content=content,
                source=source,
            )

        return DocLookupResult(performed=False)

    def _extract_minimal_snippet(self, raw_help: str, topic: str = "") -> str:
        """Keep only the smallest relevant usage/flags snippet (5-15 lines)."""
        lines = [line.rstrip() for line in raw_help.splitlines()]
        # If short enough, return as-is
        if len(lines) <= 20:
            return "\n".join(lines)

        # Look for relevant sections: USAGE, FLAGS/OPTIONS
        selected = []
        capture = False
        count = 0
        for line in lines:
            upper = line.strip().upper()
            if any(upper.startswith(h) for h in ("NAME", "SYNOPSIS", "USAGE", "OPTIONS", "FLAGS", "COMMON OPTIONS")):
                capture = True
            elif upper.startswith("DESCRIPTION") and count > 6:
                capture = False

            if capture:
                selected.append(line)
                count += 1
                if count >= 18:
                    break

        if selected:
            return "\n".join(selected)
        return "\n".join(lines[:15])

    def _generate_builtin_snippet(
        self,
        topic: str,
        exe: Optional[str],
        validation: Optional[ValidationResult],
        intent_validation: Optional[IntentValidationResult],
    ) -> tuple[Optional[str], str]:
        """Built-in minimal usage fallback when external fixture is absent."""
        t = (topic or "").lower()
        e = (exe or "").lower()

        if "paccache" in t or ("clean" in t and "cache" in t):
            return (
                "NAME\n  paccache - flexible pacman cache-cleaning utility\n\n"
                "USAGE\n  paccache [options]\n\n"
                "OPTIONS\n  -r, --remove       Clean packages\n  -k, --keep <num>   Keep <num> of each package in cache (default: 3)\n  -u, --uninstalled  Target uninstalled packages\n",
                "builtin:paccache",
            )
        elif "systemctl" in t or e == "systemctl":
            return (
                "NAME\n  systemctl - Control the systemd system and service manager\n\n"
                "USAGE\n  systemctl [OPTIONS...] COMMAND [UNIT...]\n\n"
                "COMMANDS\n  enable [UNIT...]   Enable one or more unit files\n  start [UNIT...]    Start (activate) one or more units\n"
                "OPTIONS\n  --now              Start or stop unit when enabling or disabling\n  --failed           List units in failed state\n",
                "builtin:systemctl",
            )
        elif "journalctl" in t or e == "journalctl":
            return (
                "NAME\n  journalctl - Query the systemd journal\n\n"
                "USAGE\n  journalctl [OPTIONS...] [MATCHES...]\n\n"
                "OPTIONS\n  -k, --dmesg        Show kernel messages\n  -b, --boot[=ID]    Show messages from specific boot\n  -f, --follow       Follow the journal live\n  -u, --unit=UNIT    Show messages for specified unit\n",
                "builtin:journalctl",
            )
        elif e == "gh" and "review" in t:
            return (
                "NAME\n  gh pr review - Add a review to a pull request\n\n"
                "USAGE\n  gh pr review [<number> | <url> | <branch>] [flags]\n\n"
                "FLAGS\n  -a, --approve    Approve pull request\n  -r, --request-changes\n  -c, --comment\n",
                "builtin:gh_pr_review",
            )
        elif e == "gh" and "merge" in t:
            return (
                "NAME\n  gh pr merge - Merge a pull request\n\n"
                "USAGE\n  gh pr merge [<number>] [flags]\n\n"
                "FLAGS\n  --merge    Merge commits\n  --rebase   Rebase commits\n  --squash   Squash commits\n",
                "builtin:gh_pr_merge",
            )
        elif e == "gcloud" and "firewall" in t:
            return (
                "NAME\n  gcloud compute firewall-rules create\n\n"
                "USAGE\n  gcloud compute firewall-rules create NAME --allow=PROTOCOL[:PORT] [--source-ranges=CIDR,...]\n",
                "builtin:gcloud_firewall_rules",
            )
        elif e == "pacman":
            return (
                "USAGE\n  pacman <operation> [options] [targets]\n\n"
                "OPERATIONS\n  -S (install/sync), -Q (query), -R (remove), -F (files)\n  -U (upgrade/install local package archive)\n",
                "builtin:pacman",
            )
        elif e == "git" or "git" in t:
            return (
                "USAGE\n  git pull --rebase [options]\n  git push -u <remote> <branch>\n  git checkout -b <branch>\n",
                "builtin:git",
            )
        elif e == "ln" or "symlink" in t:
            return (
                "USAGE\n  ln -s TARGET LINK_NAME\n\n"
                "NOTE\n  TARGET is the existing file/directory. LINK_NAME is the link to create.\n",
                "builtin:ln",
            )
        elif "sha256sum" in e or "checksum" in t:
            return (
                "USAGE\n  sha256sum [OPTION]... [FILE]...\n\n"
                "OPTIONS\n  -c, --check   read checksums from FILEs and check them\n",
                "builtin:sha256sum",
            )

        suggested = (intent_validation.suggested_fix if intent_validation else None) or (validation.suggested_fix if validation else None)
        if suggested:
            return f"USAGE\n  Suggested command syntax: {suggested}\n", "builtin:suggestion"

        return None, "none"
