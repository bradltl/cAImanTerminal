"""Report/prompt sanitation. Raw replay inputs must be synthetic fixtures only."""
import re

PATTERNS = [
    r'''(?i)[\w-]*(?:token|password|passwd|secret|api[_-]?key)[\w-]*\s*(?:[=:]|\s)\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
    r'(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})',
    r'''(?i)(?:Bearer|Basic)\s+[^\s'"]+''',
    r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:]+:[^\s/@]+@[^\s]+',
    r'(?:^|\s)-u\s+[^\s:]+:[^\s]+',
    r'(?i)\b(?:mysql|mysqldump|mariadb)\b[^\r\n]*\s-p[^\s]+',
]

def redact(text):
    if 'PRIVATEKEY-----' in re.sub(r'\s', '', text):
        return '[private key material withheld]'
    for pattern in PATTERNS:
        text = re.sub(pattern, '[secret redacted]', text)
    return text

def sanitize(value):
    if isinstance(value, str): return redact(value)
    if isinstance(value, dict): return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list): return [sanitize(item) for item in value]
    return value
