from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table


def generate_pairwise_comparison(
    oracle_json_path: Path | str,
    runtime_json_path: Path | str,
    console: Optional[Console] = None,
) -> Dict[str, Any]:
    """
    Compare Oracle-intent and Runtime-intent runs that used the exact same replayed initial model outputs.
    Categorizes differences into:
      - intent_domain_mismatch
      - intent_operation_mismatch
      - slot_mismatch
      - runtime_ambiguous
      - runtime_unknown
      - different_deterministic_correction
      - different_repair_outcome
      - no_material_difference
    """
    console = console or Console()
    with open(oracle_json_path, "r", encoding="utf-8") as f:
        oracle_data = json.load(f)
    with open(runtime_json_path, "r", encoding="utf-8") as f:
        runtime_data = json.load(f)

    oracle_scenarios = {s["scenario_id"]: s for s in oracle_data.get("scenarios", [])}
    runtime_scenarios = {s["scenario_id"]: s for s in runtime_data.get("scenarios", [])}
    if not oracle_data.get("model_sha256") or oracle_data.get("model_sha256") != runtime_data.get("model_sha256"):
        raise ValueError("Pairwise comparison requires identical model hashes")
    if oracle_scenarios.keys() != runtime_scenarios.keys():
        raise ValueError("Pairwise comparison requires identical scenario sets")
    provenance = oracle_data.get("provenance") or {}
    if not provenance.get("raw_artifact_sha256") or provenance != runtime_data.get("provenance"):
        raise ValueError("Pairwise comparison requires identical corpus, templates and raw replay artifact hashes")

    all_ids = list(oracle_scenarios.keys())

    differences: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {
        "intent_domain_mismatch": 0,
        "intent_operation_mismatch": 0,
        "slot_mismatch": 0,
        "runtime_ambiguous": 0,
        "runtime_unknown": 0,
        "different_deterministic_correction": 0,
        "different_repair_outcome": 0,
        "no_material_difference": 0,
    }

    staging_both_eligible = 0
    staging_oracle_only = 0
    staging_runtime_only = 0
    staging_neither = 0

    for s_id in all_ids:
        o_s = oracle_scenarios.get(s_id, {})
        r_s = runtime_scenarios.get(s_id, {})

        o_eval = o_s.get("system_evaluation") or {}
        r_eval = r_s.get("system_evaluation") or {}

        o_staging = o_eval.get("staging_eligible", False)
        r_staging = r_eval.get("staging_eligible", False)

        if o_staging and r_staging:
            staging_both_eligible += 1
        elif o_staging and not r_staging:
            staging_oracle_only += 1
        elif not o_staging and r_staging:
            staging_runtime_only += 1
        else:
            staging_neither += 1

        o_final_cmd = o_eval.get("final_command") or o_s.get("parsed_command")
        r_final_cmd = r_eval.get("final_command") or r_s.get("parsed_command")

        o_contract = o_eval.get("intent_contract") or {}
        r_contract = r_eval.get("intent_contract") or {}
        r_res = r_eval.get("runtime_intent_resolution") or {}

        r_status = r_res.get("status", "unknown")

        diff_reason = "no_material_difference"

        if r_status == "unknown":
            diff_reason = "runtime_unknown"
        elif r_status == "ambiguous":
            if o_contract.get("operation") not in ("clarify", "unknown"):
                diff_reason = "runtime_ambiguous"
        elif o_contract.get("domain") != r_contract.get("domain"):
            diff_reason = "intent_domain_mismatch"
        elif o_contract.get("operation") != r_contract.get("operation"):
            diff_reason = "intent_operation_mismatch"
        elif o_contract.get("parameters") != r_contract.get("parameters"):
            diff_reason = "slot_mismatch"
        elif o_eval.get("pipeline_path") == "deterministic_correction" and o_final_cmd != r_final_cmd:
            diff_reason = "different_deterministic_correction"
        elif o_eval.get("pipeline_path") == "llm_repair" or r_eval.get("pipeline_path") == "llm_repair":
            if o_eval.get("repair", {}).get("success") != r_eval.get("repair", {}).get("success"):
                diff_reason = "different_repair_outcome"

        category_counts[diff_reason] = category_counts.get(diff_reason, 0) + 1

        if diff_reason != "no_material_difference" or o_staging != r_staging or o_final_cmd != r_final_cmd:
            differences.append({
                "scenario_id": s_id,
                "category": diff_reason,
                "oracle_intent": f"{o_contract.get('domain')}/{o_contract.get('operation')}",
                "runtime_intent": f"{r_contract.get('domain')}/{r_contract.get('operation')}" if r_contract else r_status,
                "oracle_staging": o_staging,
                "runtime_staging": r_staging,
                "oracle_command": o_final_cmd,
                "runtime_command": r_final_cmd,
            })

    # Summary table
    table = Table(title="Pairwise Oracle vs. Runtime Intent Comparison", show_header=True, header_style="bold cyan")
    table.add_column("Difference Category", width=38)
    table.add_column("Count", justify="right", width=12)
    table.add_column("Percentage", justify="right", width=14)

    total_scenarios = len(all_ids)
    for cat, cnt in category_counts.items():
        pct = (cnt / total_scenarios * 100.0) if total_scenarios else 0.0
        table.add_row(cat, str(cnt), f"{pct:.1f}%")

    table.add_section()
    table.add_row("Total Scenarios Compared", str(total_scenarios), "100.0%")
    console.print(table)
    console.print()

    # Staging agreement table
    stg_table = Table(title="Staging Eligibility Agreement", show_header=True, header_style="bold green")
    stg_table.add_column("Classification", width=38)
    stg_table.add_column("Count", justify="right", width=12)
    stg_table.add_column("Percentage", justify="right", width=14)

    stg_table.add_row("Both Staging Eligible", str(staging_both_eligible), f"{(staging_both_eligible/total_scenarios*100.0) if total_scenarios else 0.0:.1f}%")
    stg_table.add_row("Oracle-Only Staging Eligible", str(staging_oracle_only), f"{(staging_oracle_only/total_scenarios*100.0) if total_scenarios else 0.0:.1f}%")
    stg_table.add_row("Runtime-Only Staging Eligible", str(staging_runtime_only), f"{(staging_runtime_only/total_scenarios*100.0) if total_scenarios else 0.0:.1f}%")
    stg_table.add_row("Neither Staging Eligible", str(staging_neither), f"{(staging_neither/total_scenarios*100.0) if total_scenarios else 0.0:.1f}%")
    console.print(stg_table)
    console.print()

    return {
        "total_scenarios": total_scenarios,
        "category_counts": category_counts,
        "staging_agreement": {
            "both_eligible": staging_both_eligible,
            "oracle_only": staging_oracle_only,
            "runtime_only": staging_runtime_only,
            "neither": staging_neither,
        },
        "differences": differences,
    }
