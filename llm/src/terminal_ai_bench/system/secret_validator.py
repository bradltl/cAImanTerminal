from __future__ import annotations

import re
from typing import Tuple

from .types import CommandAST, SecretCheckResult

# Patterns for detecting credentials and secrets
SECRET_PATTERNS = [
    ("github_token", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
    ("github_fine_grained_pat", r"\bgithub_pat_[A-Za-z0-9_]{82,}\b"),
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("openai_key", r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    ("bearer_token", r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})"),
    ("private_key_header", r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]


class SecretValidator:
    """
    Deterministic Secret Gate for cAIman Terminal.
    Detects embedded credentials, API tokens, and passwords in commands.
    Redacts secrets and rewrites commands safely where appropriate.
    """

    def evaluate(self, ast: CommandAST) -> SecretCheckResult:
        raw = ast.raw_command.strip()

        # 1. Check for command-line embedded passwords (e.g. mysql -u root -psecret123)
        # mysql -p<password> without space: e.g. -psecret123
        mysql_pwd_match = re.search(r"(?:^|\s)(-p[^\s]+)", raw)
        if (ast.executable in ("mysql", "mysqldump", "mariadb") or (ast.has_sudo and "mysql" in raw)) and mysql_pwd_match:
            flag_val = mysql_pwd_match.group(1)
            # If length > 2 (i.e. not just '-p'), password was supplied directly
            if len(flag_val) > 2 and flag_val != "-p":
                # Rewrite to -p so prompt asks safely interactively
                rewritten = raw.replace(flag_val, "-p")
                return SecretCheckResult(
                    secret_detected=True,
                    secret_type="command_line_password",
                    redacted_command=rewritten,
                    blocked=False,
                )

        # curl -u user:password
        curl_u_match = re.search(r"-u\s+([^\s:]+):([^\s]+)", raw)
        if curl_u_match:
            user = curl_u_match.group(1)
            rewritten = raw.replace(curl_u_match.group(0), f"-u {user}")
            return SecretCheckResult(
                secret_detected=True,
                secret_type="command_line_password",
                redacted_command=rewritten,
                blocked=False,
            )

        # 2. Check for token and API key signatures
        for sec_type, pat in SECRET_PATTERNS:
            m = re.search(pat, raw)
            if m:
                # Redact secret token
                redacted = re.sub(pat, "[REDACTED_SECRET]", raw)
                return SecretCheckResult(
                    secret_detected=True,
                    secret_type=sec_type,
                    redacted_command=redacted,
                    blocked=True,  # Disallow staging commands with hardcoded API keys
                )

        return SecretCheckResult(secret_detected=False)


def redact_secrets(command: str) -> str:
    """Utility function to scrub any secret token from logs and reports."""
    if not command:
        return ""
    scrubbed = command
    # Scrub mysql password
    scrubbed = re.sub(r"(\b(?:mysql|mariadb)\b[^-]*-p)[^\s\-]+", r"\1[REDACTED]", scrubbed)
    # Scrub token patterns
    for _, pat in SECRET_PATTERNS:
        scrubbed = re.sub(pat, "[REDACTED]", scrubbed)
    return scrubbed
