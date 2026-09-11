from __future__ import annotations

from typing import Any, Dict, List
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

from ..scoring import ScenarioScore
from ..scenario import Domain


def print_console_report(
    model_name: str,
    domain_scores: Dict[str, float],
    domain_targets: Dict[str, float],
    category_scores: Dict[str, float],
    perf_metrics: Dict[str, Any],
    scenario_scores: List[ScenarioScore],
    overall_score: float,
    safety_passed: bool,
    model_sha256: Optional[str] = None,
    console: Console | None = None,
    evaluation_mode: str = "raw",
    system_metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """Renders clean, structured terminal benchmark summary matching specification."""
    if console is None:
        console = Console()

    console.print()
    mode_tag = " [bold green](System Mode)[/bold green]" if evaluation_mode == "system" else " [bold blue](Raw Mode)[/bold blue]"
    console.rule(f"[bold cyan]Benchmark Summary: {model_name}[/bold cyan]{mode_tag}")
    if model_sha256:
        console.print(f"[dim]Weights SHA-256: {model_sha256}[/dim]")
    console.print()

    # Overall score with target status
    status_style = "bold green" if overall_score >= 90.0 and safety_passed else "bold yellow"
    safety_badge = "[bold green]SAFETY GATE PASSED[/bold green]" if safety_passed else "[bold red]SAFETY GATE FAILED[/bold red]"
    console.print(f"Overall: [{status_style}]{overall_score:.1f}%[/{status_style}]  |  {safety_badge}\n")

    # Domain Breakdown Table
    table = Table(title="Domain Scores", show_header=True, header_style="bold magenta")
    table.add_column("Domain", style="dim", width=24)
    table.add_column("Score", justify="right", width=12)
    table.add_column("Target", justify="right", width=12)
    table.add_column("Status", justify="center", width=10)

    for domain_key, score in domain_scores.items():
        target = domain_targets.get(domain_key, 0.90) * 100.0
        passed = score >= target
        status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        table.add_row(
            domain_key.capitalize(),
            f"{score:.1f}%",
            f"{target:.1f}%",
            status,
        )

    console.print(table)
    console.print()

    # Detailed Capability Breakdown
    cap_table = Table(title="Diagnostic Capabilities", show_header=True, header_style="bold blue")
    cap_table.add_column("Capability", width=28)
    cap_table.add_column("Score", justify="right", width=12)

    for cap_name, score in category_scores.items():
        cap_table.add_row(cap_name, f"{score:.1f}%")

    console.print(cap_table)
    console.print()

    # Performance Metrics
    p_table = Table(title="Performance Metrics", show_header=False)
    p_table.add_column("Metric", style="dim", width=24)
    p_table.add_column("Value", justify="right", width=16)

    p_table.add_row("Model Load Time", f"{perf_metrics.get('load_time_s', 0.0):.2f}s")
    p_table.add_row("Resident RAM", f"{perf_metrics.get('ram_mb', 0.0):.1f} MB")
    p_table.add_row("TTFT p50", f"{perf_metrics.get('ttft_p50_ms', 0.0):.1f}ms")
    p_table.add_row("TTFT p95", f"{perf_metrics.get('ttft_p95_ms', 0.0):.1f}ms")
    p_table.add_row("Throughput", f"{perf_metrics.get('tokens_per_sec', 0.0):.1f} tok/s")

    console.print(p_table)
    console.print()

    # System Pipeline Metrics (if in system mode)
    if system_metrics:
        s_table = Table(title="cAIman Terminal System Pipeline Metrics", show_header=True, header_style="bold green")
        s_table.add_column("System Pipeline Metric", width=34)
        s_table.add_column("Value", justify="right", width=16)

        s_table.add_row("Raw LLM Score", f"{system_metrics.get('raw_overall_score', 0.0):.1f}%")
        s_table.add_row("System Overall Score", f"{system_metrics.get('system_overall_score', 0.0):.1f}%")
        resp_cmds = system_metrics.get('responses_with_commands', 0)
        non_cmds = system_metrics.get('non_command_action_count', 0)
        s_table.add_row("Responses with Commands", str(resp_cmds))
        s_table.add_row("Non-command Actions", str(non_cmds))
        s_table.add_row("Initial CLI Valid Rate", f"{system_metrics.get('initial_valid_rate', 0.0):.1f}%")
        cmd_valid_rate = system_metrics.get('final_command_cli_valid_rate', 0.0)
        valid_cnt = system_metrics.get('final_command_cli_valid_count', 0)
        invalid_cnt = system_metrics.get('final_command_cli_invalid_count', 0)
        unk_cnt = system_metrics.get('final_command_cli_unknown_count', 0)
        s_table.add_row("Final Command CLI Valid Rate", f"{cmd_valid_rate:.1f}% ({valid_cnt}/{resp_cmds})")
        s_table.add_row("Command CLI Breakdown", f"Valid:{valid_cnt} Invalid:{invalid_cnt} Unknown:{unk_cnt}")
        s_table.add_row("Validator Catalog Coverage", f"{system_metrics.get('validator_catalog_coverage', 0.0):.1f}% (Spec: {system_metrics.get('specialized_validator_coverage', 0.0):.1f}%, Gen: {system_metrics.get('generic_validator_coverage', 0.0):.1f}%, Unk: {system_metrics.get('unknown_executable_rate', 0.0):.1f}%)")
        s_table.add_row("Intent Contract Coverage", f"{system_metrics.get('intent_contract_coverage', 0.0):.1f}%")
        s_table.add_row("Intent Satisfied Rate", f"{system_metrics.get('intent_satisfied_rate', 0.0):.1f}%")
        stg_rate = system_metrics.get('staging_eligible_rate', 0.0)
        stg_cnt = system_metrics.get('staging_eligible_count', 0)
        s_table.add_row("Staging Eligible Rate", f"{stg_rate:.1f}% ({stg_cnt} scenarios)")
        stg_cli_valid = system_metrics.get('staged_command_cli_valid_rate', 100.0)
        s_table.add_row("Staged Command CLI Valid Rate", f"{stg_cli_valid:.1f}%")
        s_table.add_row("Initial Stageable Rate", f"{system_metrics.get('initial_stageable_rate', 0.0):.1f}%")
        s_table.add_row("Final Stageable Rate", f"{system_metrics.get('final_stageable_rate', 0.0):.1f}%")
        s_table.add_row("CLI Valid but Intent Wrong Caught", str(system_metrics.get('cli_valid_but_intent_wrong_caught', 0)))
        sat_i = system_metrics.get('intent_satisfied_initial', 0)
        part_i = system_metrics.get('intent_partial_initial', 0)
        mis_i = system_metrics.get('intent_mismatch_initial', 0)
        unk_i = system_metrics.get('intent_unknown_initial', 0)
        s_table.add_row("Initial Intent Breakdown", f"Sat:{sat_i} Part:{part_i} Mis:{mis_i} Unk:{unk_i}")
        sat_f = system_metrics.get('intent_satisfied_final', 0)
        part_f = system_metrics.get('intent_partial_final', 0)
        mis_f = system_metrics.get('intent_mismatch_final', 0)
        unk_f = system_metrics.get('intent_unknown_final', 0)
        s_table.add_row("Final Intent Breakdown", f"Sat:{sat_f} Part:{part_f} Mis:{mis_f} Unk:{unk_f}")
        det_app = system_metrics.get('deterministic_corrections_applied', 0)
        det_succ = system_metrics.get('deterministic_correction_successes', 0)
        det_fail_rate = system_metrics.get('deterministic_correction_failure_rate', 0.0)
        s_table.add_row("Deterministic Corrections", f"{det_succ}/{det_app} (Fail Rate: {det_fail_rate:.1f}%)")
        s_table.add_row("Avoided Second Inference", str(system_metrics.get('commands_avoiding_second_inference', 0)))
        s_table.add_row("Commands Requiring Repair", str(system_metrics.get('commands_requiring_repair', 0)))
        rep_att = system_metrics.get('repair_attempts', 0)
        rep_succ = system_metrics.get('true_repair_successes', system_metrics.get('repair_successes', 0))
        rep_fail = system_metrics.get('failed_repairs', 0)
        rep_unk = system_metrics.get('unverified_repairs', 0)
        rep_rate = system_metrics.get('repair_success_rate', 0.0)
        s_table.add_row("LLM Repair Success Rate", f"{rep_rate:.1f}% ({rep_succ}/{rep_att})")
        s_table.add_row("Repair Outcome Breakdown", f"Success:{rep_succ} Failed:{rep_fail} Unverified:{rep_unk}")
        irep_att = system_metrics.get('intent_repair_attempts', 0)
        irep_succ = system_metrics.get('intent_repair_successes', 0)
        irep_rate = system_metrics.get('intent_repair_success_rate', 0.0)
        s_table.add_row("Intent Repair Success Rate", f"{irep_rate:.1f}% ({irep_succ}/{irep_att})")
        docs_succ_cnt = system_metrics.get('docs_lookup_success', 0)
        docs_req_cnt = system_metrics.get('docs_requested', 0)
        s_table.add_row("Doc Lookup Success Rate", f"{system_metrics.get('docs_lookup_success_rate', 0.0):.1f}% ({docs_succ_cnt}/{docs_req_cnt})")
        cat_gen = system_metrics.get('catastrophic_generated', 0)
        cat_blk = system_metrics.get('catastrophic_blocked', 0)
        cat_rate = system_metrics.get('catastrophic_block_rate', 100.0)
        s_table.add_row("Catastrophic Block Rate", f"{cat_rate:.1f}% ({cat_blk}/{cat_gen})")
        dang_gen = system_metrics.get('dangerous_commands_generated', 0)
        dang_blk = system_metrics.get('dangerous_commands_blocked', 0)
        dang_esc = system_metrics.get('dangerous_command_escape_count', 0)
        dang_rate = system_metrics.get('dangerous_command_escape_rate', 0.0)
        s_table.add_row("Dangerous Command Block Rate", f"{100.0 - dang_rate:.1f}% ({dang_blk}/{dang_gen})")
        s_table.add_row("Dangerous Command Escapes", f"{dang_esc} (Rate: {dang_rate:.1f}%)")
        bd_gen = system_metrics.get('block_device_mutations_generated', 0)
        bd_blk = system_metrics.get('block_device_mutations_blocked', 0)
        s_table.add_row("Block Device Mutations Blocked", f"{bd_blk}/{bd_gen}")
        fw_gen = system_metrics.get('firewall_destructive_generated', 0)
        fw_blk = system_metrics.get('firewall_destructive_blocked', 0)
        s_table.add_row("Firewall Mutations Blocked", f"{fw_blk}/{fw_gen}")
        unexp_blk = system_metrics.get('unexpected_destructive_operations', 0)
        s_table.add_row("Unexpected Destructive Blocked", str(unexp_blk))
        sec_gen = system_metrics.get('secret_exposures_generated', 0)
        sec_blk = system_metrics.get('secret_exposures_blocked', 0)
        sec_rate = system_metrics.get('secret_block_rate', 100.0)
        s_table.add_row("Secret Block Rate", f"{sec_rate:.1f}% ({sec_blk}/{sec_gen})")
        s_table.add_row("Safe Commands Falsely Blocked", str(system_metrics.get('safe_commands_falsely_blocked', 0)))
        s_table.add_row("False Positive Block Rate", f"{system_metrics.get('false_positive_block_rate', 0.0):.1f}%")
        s_table.add_row("Final Usable Rate", f"{system_metrics.get('final_usable_rate', 0.0):.1f}%")
        s_table.add_row("Initial Model Inference p50 / p95", f"{system_metrics.get('initial_inference_p50_ms', 0.0):.1f}ms / {system_metrics.get('initial_inference_p95_ms', 0.0):.1f}ms")
        s_table.add_row("Deterministic Host Overhead p50 / p95", f"{system_metrics.get('host_overhead_p50_ms', 0.0):.1f}ms / {system_metrics.get('host_overhead_p95_ms', 0.0):.1f}ms")
        s_table.add_row("Normal Path End-to-End p50 / p95", f"{system_metrics.get('normal_path_p50_ms', 0.0):.1f}ms / {system_metrics.get('normal_path_p95_ms', 0.0):.1f}ms")
        s_table.add_row("Deterministic Corr Path p50 / p95", f"{system_metrics.get('deterministic_correction_p50_ms', 0.0):.1f}ms / {system_metrics.get('deterministic_correction_p95_ms', 0.0):.1f}ms")
        s_table.add_row("LLM Repair Path Latency p50 / p95", f"{system_metrics.get('llm_repair_path_p50_ms', 0.0):.1f}ms / {system_metrics.get('llm_repair_path_p95_ms', 0.0):.1f}ms")
        s_table.add_row("Total End-to-End Latency p50 / p95", f"{system_metrics.get('total_end_to_end_p50_ms', 0.0):.1f}ms / {system_metrics.get('total_end_to_end_p95_ms', 0.0):.1f}ms")

        console.print(s_table)
        console.print()

        # Runtime Intent Resolution Metrics
        if system_metrics.get("intent_source") == "runtime" or system_metrics.get("runtime_intent_resolved_count", 0) > 0:
            rt_table = Table(title="cAIman Terminal Runtime Intent Resolution Metrics", show_header=True, header_style="bold magenta")
            rt_table.add_column("Runtime Intent Metric", width=34)
            rt_table.add_column("Value", justify="right", width=20)

            rt_table.add_row("Intent Resolution Source", str(system_metrics.get("intent_source", "runtime")))
            rt_table.add_row("Runtime Intent Coverage", f"{system_metrics.get('runtime_intent_coverage', 0.0):.1f}%")
            rt_table.add_row("Runtime Intent Precision", f"{system_metrics.get('runtime_intent_precision', 0.0):.1f}%")
            rt_table.add_row("Intent Domain Accuracy", f"{system_metrics.get('intent_domain_accuracy', 0.0):.1f}%")
            rt_table.add_row("Intent Operation Accuracy", f"{system_metrics.get('intent_operation_accuracy', 0.0):.1f}%")
            rt_table.add_row("Slot Extraction Accuracy", f"{system_metrics.get('slot_extraction_accuracy', 0.0):.1f}%")
            rt_table.add_row("Missing Slot Clarification Rate", f"{system_metrics.get('missing_slot_clarification_rate', 0.0):.1f}%")
            rt_table.add_row("False Resolution Rate", f"{system_metrics.get('false_resolution_rate', 0.0):.1f}%")
            rt_table.add_row("Supported Intent Coverage", f"{system_metrics.get('supported_intent_coverage', 0.0):.1f}%")
            rt_table.add_row("Supported Intent Precision", f"{system_metrics.get('supported_intent_precision', 0.0):.1f}%")
            if system_metrics.get("expansion_intent_count", 0) > 0:
                rt_table.add_row("Expansion Intent Coverage", f"{system_metrics.get('expansion_intent_coverage', 0.0):.1f}%")
                rt_table.add_row("Expansion Intent Precision", f"{system_metrics.get('expansion_intent_precision', 0.0):.1f}%")
            rt_table.add_row("False Ambiguity Count", str(system_metrics.get("false_ambiguity_count", 0)))
            rt_table.add_row("Incorrect Medium-Confidence", str(system_metrics.get("incorrect_medium_confidence_count", 0)))
            rt_table.add_row("Context Resolution (Succ/Att)", f"{system_metrics.get('context_resolution_successes', 0)}/{system_metrics.get('context_resolution_attempts', 0)}")
            h_cnt = system_metrics.get("high_confidence_resolutions", 0)
            m_cnt = system_metrics.get("medium_confidence_resolutions", 0)
            l_cnt = system_metrics.get("low_confidence_resolutions", 0)
            rt_table.add_row("Confidence Breakdown", f"HIGH:{h_cnt} MED:{m_cnt} LOW:{l_cnt}")
            rt_table.add_row("Context-Resolved References", str(system_metrics.get("context_resolved_reference_count", 0)))
            rt_table.add_row("Clarification Requests", str(system_metrics.get("clarification_requests_count", 0)))
            rt_table.add_row("Incorrect HIGH-Confidence Count", str(system_metrics.get("incorrect_high_confidence_count", 0)))

            console.print(rt_table)
            console.print()

            # Incorrect HIGH-confidence cases table
            inc_cases = system_metrics.get("incorrect_high_confidence_cases", [])
            if inc_cases:
                inc_table = Table(title="Incorrect HIGH-Confidence Cases", show_header=True, header_style="bold red")
                inc_table.add_column("Scenario ID", width=16)
                inc_table.add_column("User Text", width=36)
                inc_table.add_column("Requested Op", width=18)
                inc_table.add_column("Resolved Op", width=18)
                for case in inc_cases:
                    inc_table.add_row(
                        str(case.get("scenario_id", "")),
                        str(case.get("user_text", ""))[:35],
                        str(case.get("requested_operation", "")),
                        str(case.get("resolved_operation", "")),
                    )
                console.print(inc_table)
                console.print()

            # Confusion Matrix summary (discrepancies where requested != resolved)
            c_mat = system_metrics.get("intent_confusion_matrix", {})
            mismatches = []
            for gold_op, pred_map in c_mat.items():
                for pred_op, cnt in pred_map.items():
                    if gold_op != pred_op and cnt > 0:
                        if (gold_op == "multi_turn_git_branch" and pred_op in ("create_branch", "push_set_upstream")) or \
                           (gold_op == "stash" and pred_op in ("stash", "stash_pop")) or \
                           (gold_op == "disk_usage" and pred_op in ("disk_usage", "diagnose_disk_usage")) or \
                           (gold_op == "clarify" and pred_op in ("restart_service", "clarify")):
                            continue
                        mismatches.append((gold_op, pred_op, cnt))
            if mismatches:
                cm_table = Table(title="Intent Resolution Confusion Matrix (Mismatches)", show_header=True, header_style="bold yellow")
                cm_table.add_column("Requested Operation", width=28)
                cm_table.add_column("Resolved Operation", width=28)
                cm_table.add_column("Count", justify="right", width=8)
                for g_op, r_op, c in sorted(mismatches, key=lambda x: -x[2]):
                    cm_table.add_row(g_op, r_op, str(c))
                console.print(cm_table)
                console.print()

    # Failures / Notes
    failures = [s for s in scenario_scores if not s.passed]
    if failures:
        console.print("[bold red]FAILED SCENARIOS:[/bold red]")
        for f in failures:
            notes_str = "; ".join(f.notes[:2]) if f.notes else "Below passing threshold"
            console.print(f"  [red]✗[/red] [bold]{f.scenario_id}[/bold] ({f.scenario_name}): {notes_str}")
    else:
        console.print("[bold green]✔ All scenarios passed threshold criteria![/bold green]")
    console.print()
