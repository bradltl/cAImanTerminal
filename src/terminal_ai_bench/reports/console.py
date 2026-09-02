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
    console: Console | None = None,
) -> None:
    """Renders clean, structured terminal benchmark summary matching specification."""
    if console is None:
        console = Console()

    console.print()
    console.rule(f"[bold cyan]Benchmark Summary: {model_name}[/bold cyan]")
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
