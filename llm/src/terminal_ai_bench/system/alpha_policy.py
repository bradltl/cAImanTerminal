"""Independent alpha-v1 reference; no Rust invocation or recorded verdicts.

The shared manifest is policy data, not an oracle. Parsing, contract resolution,
validation, correction and final stageability are independently implemented here.
Research pipeline behavior remains separately available.
"""
import copy
import json
import re
import shlex
import unicodedata
from pathlib import Path
from ..privacy import redact, sanitize
from .command_parser import check_shell_syntax

ROOT = Path(__file__).resolve().parents[4]
POLICY = json.loads((ROOT / "terminal/resources/alpha-policy.json").read_text())
VERSION = "alpha-v1"


def parse(text):
    if not text or len(text.encode()) > 4096 or "$" in text or "`" in text:
        return None
    if any(unicodedata.category(c) == "Cc" or ord(c) in (0x61c, 0xfeff) or 0x200b <= ord(c) <= 0x200f or 0x2028 <= ord(c) <= 0x202e or 0x2060 <= ord(c) <= 0x206f for c in text):
        return None
    quote, escaped, start, parts = None, False, 0, []
    for i, c in enumerate(text):
        if escaped:
            escaped = False
            if quote is None and c in "*?[{~": return None
            continue
        if c == "\\" and quote != "'": escaped = True; continue
        if quote:
            if c == quote: quote = None
            continue
        if c in "\"'": quote = c; continue
        if c in ";&<>()*?[{~" or (c == "#" and (i == 0 or text[i-1].isspace())):
            return None
        if c == "|": parts.append(text[start:i]); start = i + 1
    if quote or escaped: return None
    parts.append(text[start:])
    # Bash pipeline negation is syntax, not an executable named "!".
    if any(re.match(r"\s*!(?:\s|$)", part) for part in parts): return None
    try:
        commands = [shlex.split(p) for p in parts]
    except ValueError:
        return None
    if any(not words or "=" in words[0] for words in commands): return None
    if not check_shell_syntax(text)[0]: return None
    return commands


def resolve(request, context, host, passive):
    explain = {"kind": "explain_or_clarify"}
    if passive or context["remote"]: return explain
    text = request.strip().lstrip("@").strip()
    lower = text.lower()
    if "?" in lower or any(f" {word} " in f" {lower} " for word in ["don't", "do not", "not", "never", "explain", "what", "why", "how", "dangerous", "without", "continue"]): return explain
    tasks = {
        "show disk usage": ["df -h", "df -hT"], "show me disk usage": ["df -h", "df -hT"], "disk usage": ["df -h", "df -hT"],
        "show memory usage": ["free -h"], "memory usage": ["free -h"],
        "list files": ["ls", "ls -la"], "show files": ["ls", "ls -la"], "list the files": ["ls", "ls -la"],
        "list files recursively": ["ls -R", "ls --recursive"],
        "show current directory": ["pwd"], "print working directory": ["pwd"], "show git status": ["git status"],
    }
    if lower in ("update my system", "upgrade my system") and host["package_manager"] == "pacman":
        tasks[lower] = ["pacman -Syu" if host["root"] else "sudo pacman -Syu"]
    if lower in tasks: return {"kind": "alternatives", "value": tasks[lower]}
    words = re.findall(r"[^\W_]+", lower)
    is_editor = "editor" in words and any(w in words for w in ["terminal", "text", "file"])
    if not is_editor and not any(w in words for w in ["install", "uninstall", "remove", "upgrade", "package"]) and ("readme" in words or ".md" in lower or "markdown file" in lower or "text file" in lower) and any(w in words for w in ["read", "see", "view", "show", "contents", "cat", "less"]):
        return {"kind": "read_file", "value": lower}
    return {"kind": "exact_command", "value": text} if parse(text) else explain


def names_file(query, name):
    try: words = shlex.split(query)
    except ValueError: words = []
    if any((word[2:] if word.startswith("./") else word).lower() == name.lower() for word in words): return True
    return any(c.isspace() for c in name) and re.search(r"(?<![\w./-])" + re.escape(name.lower()) + r"(?![\w./-])", query.lower()) is not None


def intent_matches(contract, candidate, commands):
    kind, value = contract["kind"], contract.get("value")
    if kind == "exact_command": return candidate == value
    if kind == "alternatives": return candidate in value
    if kind == "read_file" and len(commands) == 1 and len(commands[0]) == 2 and commands[0][0] in ("cat", "less"):
        name = commands[0][1]
        if not name.startswith("./"): return False
        name = name[2:]
        try: generic_readme = any(word.lower() == "readme" for word in shlex.split(value))
        except ValueError: generic_readme = False
        return bool(name) and "/" not in name and (names_file(value, name) or (generic_readme and name.lower() == "readme.md"))
    return False


def cli(commands, host):
    for words in commands:
        sudo = words[0] == "sudo"
        if sudo:
            if "sudo" not in host["installed"]: return "invalid"
            words = words[1:]
        if not words: return "invalid"
        exe, args = words[0], words[1:]
        profile = POLICY["commands"].get(exe)
        if profile is None: return "unknown"
        if exe not in host["installed"]: return "invalid"
        if "exact_args" in profile:
            if exe == "pacman" and (host["package_manager"] != "pacman" or not (sudo or host["root"])): return "invalid"
            if args != profile["exact_args"]: return "invalid"
            continue
        prefix = profile.get("prefix", [])
        if args[:len(prefix)] != prefix: return "invalid"
        operands, options = 0, True
        for arg in args[len(prefix):]:
            if options and arg == "--": options = False; continue
            if options and arg.startswith("-") and arg != "-":
                if arg not in profile["flags"] and not (not arg.startswith("--") and all(c.isascii() and c.isalpha() and f"-{c}" in profile["flags"] for c in arg[1:])): return "invalid"
            else: operands += 1
        if not profile["min_operands"] <= operands <= profile["max_operands"]: return "invalid"
    return "valid"


def protected(arg):
    if arg.startswith("~") or ".." in arg: return True
    clean = "/".join(p for p in arg.split("/") if p not in ("", "."))
    return arg.startswith("/") and (clean in ("", "*", "home", "var") or any(clean == root or clean.startswith(root + "/") for root in "etc usr boot dev proc sys bin sbin lib lib64 var".split()))


def risk(commands, secret):
    if secret: return "blocked"
    level = 0
    for words in commands:
        if words[0] == "sudo":
            level = 2; words = words[1:]
            if not words or words[0].startswith("-"): return "blocked"
        exe, args = words[0], words[1:]
        has = lambda word: word in args
        short = lambda char: any(a.startswith("-") and not a.startswith("--") and char in a for a in args)
        if "/" in exe or not exe.isascii(): return "blocked"
        if exe == "command" and (not args or args[0] not in ("-v", "-V")): return "blocked"
        if exe in "bash sh zsh fish python python3 perl ruby node awk gawk mawk sed eval exec env xargs watch nohup timeout busybox doas su pkexec ssh mosh tmux screen source .".split(): return "blocked"
        if any(s in word for word in words for s in ("/etc/shadow", "/etc/gshadow", "id_rsa", "id_ed25519", ".gnupg", ".aws/credentials")): return "blocked"
        if exe.startswith("mkfs") or exe in "dd wipefs shred mkswap fdisk parted".split(): return "blocked"
        removing = exe in ("rm", "rmdir") or (exe == "find" and has("-delete"))
        if (removing or exe in "chmod chown chgrp mv cp install truncate tee".split()) and any(protected(a) for a in args): return "blocked"
        if exe == "kill" and any(a in ("1", "0", "-1") for a in args): return "blocked"
        if exe == "mysql" and any((a.startswith("-p") and len(a) > 2) or a.startswith("--password=") for a in args): return "blocked"
        package_remove = (exe == "pacman" and (has("--remove") or short("R"))) or (exe in ("apt", "apt-get", "dnf", "yum") and any(has(a) for a in ("remove", "purge", "autoremove")))
        if package_remove and any(a in "glibc libc6 systemd bash linux pacman coreutils".split() for a in args): return "blocked"
        if exe == "pacman" and (short("S") or has("--sync")) and (short("y") or has("--refresh")) and not (short("u") or has("--sysupgrade")): return "blocked"
        if (exe == "find" and any(has(a) for a in ("-exec", "-execdir", "-ok"))) or (exe == "git" and has("-c")): return "blocked"
        package_write = exe in "pacman apt apt-get dnf yum zypper apk".split() and (any(a in ("update", "upgrade", "install", "full-upgrade") for a in args) or (exe == "pacman" and (has("--sync") or has("--upgrade") or short("S") or short("U"))))
        if removing or package_remove or package_write or exe in "chmod chown chgrp mount umount reboot shutdown poweroff iptables nft ufw mkinitcpio".split() or (exe == "systemctl" and any(a in "start stop restart enable disable mask".split() for a in args)) or (exe == "git" and any(has(a) for a in ("--hard", "--force", "-f"))): level = 2
        elif level == 0 and exe not in "ls pwd cat head tail wc sort uniq grep rg find du df free ps ss uname whoami id which type help man stat file uptime".split(): level = 1
    return ["normal", "caution", "elevated"][level]


def skipped():
    return dict(parser="skipped", cli="skipped", intent="skipped", safety="skipped", secret="skipped", risk="unknown")


def check(candidate, contract, host):
    result = skipped()
    secret = redact(candidate) != candidate or "[secret redacted]" in candidate
    result["secret"] = "blocked" if secret else "clean"
    commands = parse(candidate)
    if not commands:
        result.update(parser="invalid", risk="blocked")
        return result
    level = risk(commands, secret)
    result.update(parser="valid", cli=cli(commands, host), intent="satisfied" if intent_matches(contract, candidate, commands) else "mismatch", safety="blocked" if level == "blocked" else "approved", risk=level)
    return result


def evaluate(fixture):
    if fixture["policy"] != VERSION: raise ValueError("Unsupported policy version")
    if "response" in fixture:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result: raise ValueError("duplicate field")
                result[key] = value
            return result
        try:
            raw = fixture["response"]
            if len(raw.encode()) > 16384: raise ValueError("oversized response")
            response = json.loads(raw, object_pairs_hook=unique)
            if not isinstance(response, dict) or set(response) - {"action", "command", "explanation", "question", "plan"}: raise ValueError("schema")
            for field in ("command", "explanation", "question"):
                if response.get(field) is not None and not isinstance(response[field], str): raise ValueError("type")
            if response.get("plan") is not None and (not isinstance(response["plan"], list) or not all(isinstance(s, str) for s in response["plan"])): raise ValueError("plan")
            action = response.get("action")
            required = {"suggest_command":"command", "explain":"explanation", "clarify":"question"}.get(action)
            if not required or not (response.get(required) or "").strip(): raise ValueError("action")
            if action != "suggest_command" and response.get("command") is not None: raise ValueError("command")
            prose = " ".join([response.get("explanation") or "", response.get("question") or "", " ".join(response.get("plan") or [])]).lower()
            if any(phrase in prose for phrase in ["what did you expect", "what do you expect", "you should know", "obviously", "as i already told you", "when i run", "i ran ", "i executed "]): raise ValueError("prose contract")
        except (ValueError, TypeError, AttributeError):
            return dict(response_schema="invalid", trace=None, stageable=False)
        if response.get("command") is None: return dict(response_schema="valid", trace=None, stageable=False)
        nested = {k:v for k,v in fixture.items() if k != "response"}
        nested["candidate"] = response["command"]
        trace = evaluate(nested)
        return dict(response_schema="valid", trace=trace, stageable=trace["stageable"])
    request, candidate, context, host = (fixture[k] for k in ("request", "candidate", "context", "host"))
    passive = fixture.get("passive", False)
    contract = resolve(request, context, host, passive)
    current = context["at_prompt"] and not context["remote"] and not fixture.get("cancelled", False) and all(len(s.encode()) <= 4096 for s in (request, context["input"], context["cwd"]))
    initial = check(candidate, contract, host) if current else skipped()
    final, correction = copy.deepcopy(initial), None
    if initial["parser"] == "valid" and initial["secret"] == "clean" and initial["safety"] == "approved" and initial["cli"] == "invalid" and contract["kind"] == "alternatives":
        choice = contract["value"][0]
        original, replacement = parse(candidate), parse(choice)
        if len(original) == 1 and original[0][0] == replacement[0][0]:
            candidate, correction = choice, "canonical_task_options"
            final = check(candidate, contract, host)
    stageable = current and not passive and all(final[k] == v for k, v in dict(parser="valid", cli="valid", intent="satisfied", safety="approved", secret="clean").items())
    context_status = "current" if current else "rejected"
    journal = context.get("journal", [])
    if stageable and journal and journal[-1]["exit_code"] != 0 and journal[-1]["command"].strip() == candidate.strip():
        stageable, context_status = False, "previous_failure"
    return sanitize(dict(policy=VERSION, contract=contract, context=context_status, initial=initial, correction=correction, final_checks=final, stageable=stageable, final_command=candidate if stageable else None))
