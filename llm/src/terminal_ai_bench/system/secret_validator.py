"""Reference gate shares privacy signatures; secret rewrites never authorize staging."""
from ..privacy import redact
from .types import CommandAST, SecretCheckResult


class SecretValidator:
    def evaluate(self, ast: CommandAST) -> SecretCheckResult:
        raw = ast.raw_command
        scrubbed = redact(raw)
        detected = scrubbed != raw or '[secret redacted]' in raw
        return SecretCheckResult(secret_detected=detected, secret_type='embedded_credential' if detected else None, redacted_command=scrubbed if detected else None, blocked=detected)


def redact_secrets(command: str) -> str:
    return redact(command or '')
