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
        s_table.add_row("Initial CLI Valid Rate", f"{system_metrics.get('initial_valid_rate', 0.0):.1f}%")
        s_table.add_row("Final CLI Valid Rate", f"{system_metrics.get('final_valid_rate', 0.0):.1f}%")
        s_table.add_row("Intent Contract Coverage", f"{system_metrics.get('intent_contract_coverage', 0.0):.1f}%")
        s_table.add_row("Intent Satisfied Rate", f"{system_metrics.get('intent_satisfied_rate', 0.0):.1f}%")
        s_table.add_row("Staging Eligible Rate", f"{system_metrics.get('staging_eligible_rate', 0.0):.1f}%")
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
        s_table.add_row("Commands Requiring Repair", str(system_metrics.get('commands_requiring_repair', 0)))
        rep_att = system_metrics.get('repair_attempts', 0)
        rep_succ = system_metrics.get('repair_successes', 0)
        rep_rate = system_metrics.get('repair_success_rate', 0.0)
        s_table.add_row("Repair Success Rate", f"{rep_rate:.1f}% ({rep_succ}/{rep_att})")
        irep_att = system_metrics.get('intent_repair_attempts', 0)
        irep_succ = system_metrics.get('intent_repair_successes', 0)
        irep_rate = system_metrics.get('intent_repair_success_rate', 0.0)
        s_table.add_row("Intent Repair Success Rate", f"{irep_rate:.1f}% ({irep_succ}/{irep_att})")
        s_table.add_row("Doc Lookup Rate", f"{system_metrics.get('doc_lookup_rate', 0.0):.1f}%")
        cat_gen = system_metrics.get('catastrophic_generated', 0)
        cat_blk = system_metrics.get('catastrophic_blocked', 0)
        cat_rate = system_metrics.get('catastrophic_block_rate', 100.0)
        s_table.add_row("Catastrophic Block Rate", f"{cat_rate:.1f}% ({cat_blk}/{cat_gen})")
        sec_gen = system_metrics.get('secret_exposures_generated', 0)
        sec_blk = system_metrics.get('secret_exposures_blocked', 0)
        sec_rate = system_metrics.get('secret_block_rate', 100.0)
        s_table.add_row("Secret Block Rate", f"{sec_rate:.1f}% ({sec_blk}/{sec_gen})")
        s_table.add_row("Safe Commands Falsely Blocked", str(system_metrics.get('safe_commands_falsely_blocked', 0)))
        s_table.add_row("False Positive Block Rate", f"{system_metrics.get('false_positive_block_rate', 0.0):.1f}%")
        s_table.add_row("Final Usable Rate", f"{system_metrics.get('final_usable_rate', 0.0):.1f}%")
        s_table.add_row("System Pipeline Latency p50", f"{system_metrics.get('latency_p50_ms', 0.0):.1f}ms")
        s_table.add_row("System Pipeline Latency p95", f"{system_metrics.get('latency_p95_ms', 0.0):.1f}ms")

        console.print(s_table)
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
