"""Targeted fault injection in temporary copies, never the working source tree.

Run after cargo fmt. Each mutant must compile and fail a security assertion.
These four mutants measure only the named guardrails, not global mutation coverage.
"""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MUTANTS = [
    ("secret", "secrets.rs", r'if contains\(text\) \|\| text.contains\("\[secret redacted\]"\) \{', "if false {"),
    ("intent", "intent.rs", r'Self::ExplainOrClarify => false,', "Self::ExplainOrClarify => true,"),
    ("passive-repair", "worker.rs", r'if request.passive \{\s*return Err\(error\);\s*\}', "if false { return Err(error); }"),
    ("wrapper", "host.rs", r'bail!\("Interpreter/wrapper commands need manual review and cannot be staged"\);', "// removed wrapper gate"),
]

def main():
    # Never replace the working tree's binaries with a mutant, even transiently.
    build = tempfile.TemporaryDirectory(prefix="caiman-mutant-build-")
    env = {**os.environ, "CARGO_TARGET_DIR": build.name}
    for name, filename, pattern, replacement in MUTANTS:
        with tempfile.TemporaryDirectory(prefix="caiman-mutant-") as temp:
            copy = Path(temp)
            for file in ["Cargo.toml", "Cargo.lock"]:
                shutil.copy2(ROOT / file, copy / file)
            shutil.copytree(ROOT / "terminal", copy / "terminal")
            target = copy / "terminal/src" / filename
            changed, count = re.subn(pattern, lambda _: replacement, target.read_text())
            assert count == 1, (name, "mutation target changed", count)
            target.write_text(changed)  # Mechanical mutation of a disposable copy.
            result = subprocess.run(["cargo", "test", "--offline", "--locked", "--no-default-features", "--test", "adversarial"], cwd=copy, env=env, text=True, capture_output=True, timeout=120)
            assert result.returncode != 0 and "test result: FAILED" in result.stdout, (name, result.stdout, result.stderr)
            print(f"{name}: killed by adversarial tests")

if __name__ == "__main__":
    main()
