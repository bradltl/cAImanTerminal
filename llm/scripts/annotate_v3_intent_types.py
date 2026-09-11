#!/usr/bin/env python3
"""
Add intent_type field to existing intent_contract blocks in scenarios_v3 YAML files.

Classification rules:
- 'expansion': scenarios whose name starts with 'Expansion intent:' or 'In-scope expansion:'
  These are operations not yet fully registered in CANONICAL_INTENT_SPECS.
- 'supported': all other scenarios — the operation is fully registered, resolved, and validated.

This runs after add_v3_intent_contracts.py has already injected intent_contract blocks.
"""

import argparse
import re
import sys
from pathlib import Path


# Expansion scenario IDs (identified by scenario name prefix in YAML)
# We derive these dynamically from the YAML content.


def classify_scenario(content: str, scenario_id: str) -> str:
    """Return 'expansion' or 'supported' for a scenario based on its name."""
    m = re.search(r"^name:\s+'?(.+?)'?\s*$", content, re.MULTILINE)
    if not m:
        return "supported"
    name = m.group(1).strip("'\"")
    # Expansion heuristics: name starts with expansion keywords
    expansion_prefixes = (
        "Expansion intent:",
        "In-scope expansion:",
        "expansion intent:",
        "in-scope expansion:",
    )
    for prefix in expansion_prefixes:
        if name.startswith(prefix):
            return "expansion"
    return "supported"


def process_file(path: Path, dry_run: bool = False) -> bool:
    """Add or update intent_type in the top-level intent_contract block."""
    content = path.read_text(encoding="utf-8")

    m = re.match(r"id:\s+(\S+)", content)
    if not m:
        return False
    scenario_id = m.group(1)

    intent_type = classify_scenario(content, scenario_id)

    # Check if intent_contract block exists
    if "intent_contract:" not in content:
        print(f"WARNING: no intent_contract in {path.name}", file=sys.stderr)
        return False

    # Check if intent_type already present and correct
    ic_match = re.search(r"^intent_contract:\n((?:  .+\n)*)", content, re.MULTILINE)
    if not ic_match:
        return False

    ic_block = ic_match.group(0)

    # If intent_type already present and correct, skip
    existing_type_m = re.search(r"  intent_type:\s+(\S+)", ic_block)
    if existing_type_m:
        if existing_type_m.group(1) == intent_type:
            return False
        # Wrong value — replace it
        new_ic_block = re.sub(r"  intent_type:\s+\S+", f"  intent_type: {intent_type}", ic_block)
    else:
        # Add intent_type as first field after intent_contract:
        # Insert after "intent_contract:\n" line
        new_ic_block = ic_block.replace(
            "intent_contract:\n",
            f"intent_contract:\n  intent_type: {intent_type}\n",
            1,
        )

    if new_ic_block == ic_block:
        return False

    new_content = content.replace(ic_block, new_ic_block, 1)

    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Add intent_type (supported|expansion) to scenarios_v3 intent_contract blocks"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--scenarios-dir",
        default=str(Path(__file__).parent.parent / "scenarios_v3"),
    )
    args = parser.parse_args()

    scenarios_dir = Path(args.scenarios_dir)
    if not scenarios_dir.exists():
        print(f"ERROR: {scenarios_dir}", file=sys.stderr)
        sys.exit(1)

    modified = 0
    unchanged = 0
    expansion_count = 0
    supported_count = 0

    for yaml_file in sorted(scenarios_dir.rglob("*.yaml")):
        content = yaml_file.read_text()
        intent_type = classify_scenario(content, yaml_file.stem)
        if intent_type == "expansion":
            expansion_count += 1
        else:
            supported_count += 1

        changed = process_file(yaml_file, dry_run=args.dry_run)
        if changed:
            modified += 1
            verb = "would modify" if args.dry_run else "modified"
            print(f"  {verb} [{intent_type}]: {yaml_file.name}")
        else:
            unchanged += 1

    verb = "Would modify" if args.dry_run else "Modified"
    print(f"\n{verb} {modified} files, {unchanged} unchanged.")
    print(f"Expansion scenarios: {expansion_count}, Supported scenarios: {supported_count}")


if __name__ == "__main__":
    main()
