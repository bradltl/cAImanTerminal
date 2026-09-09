from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.table import Table

from .runner import BenchmarkRunner
from .scenario import load_all_scenarios
from .tool_runtime import ToolRequest, ToolRuntime


@click.group()
def main():
    """terminal-ai-bench: Model evaluation and benchmarking harness for local terminal AI."""
    pass


@main.command(name="run")
@click.argument("model")
@click.option("--domain", "-d", help="Filter scenarios by domain (bash, arch, gcloud, gh, etc.)")
@click.option("--scenario", "-s", help="Run a specific scenario by ID (e.g. arch-001)")
@click.option("--scenarios-dir", default="scenarios", help="Path to scenarios directory")
@click.option("--mock", is_flag=True, help="Force mock runtime instead of loading weights")
@click.option("--persona", default="perfect", type=click.Choice(["perfect", "imperfect", "unsafe"]), help="Mock response persona")
def run_command(model: str, domain: Optional[str], scenario: Optional[str], scenarios_dir: str, mock: bool, persona: str):
    """Run benchmark against a candidate model."""
    runner = BenchmarkRunner(scenarios_dir=scenarios_dir)
    try:
        runner.run(
            model_name=model,
            domain=domain,
            scenario_id=scenario,
            mock_mode=mock or (model == "mock"),
            mock_persona=persona,
        )
    except Exception as exc:
        console = Console()
        console.print(f"[bold red]Benchmark Error:[/bold red] {exc}")
        raise click.Abort()


@main.command(name="pull")
@click.argument("model")
@click.option("--url", help="Direct download URL for GGUF model")
@click.option("--models-config", default="config/models.yaml", help="Path to models configuration")
@click.option("--output-dir", default="models", help="Directory to save downloaded GGUF file")
def pull_command(model: str, url: Optional[str], models_config: str, output_dir: str):
    """Download a GGUF model weights file to test against."""
    import urllib.request
    from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
    import yaml

    console = Console()
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with open(models_config, "r", encoding="utf-8") as f:
        models_data = yaml.safe_load(f).get("models", {})

    alias_map = {
        "gemma3-1b": "gemma-3-1b",
        "gemma3": "gemma-3-1b",
        "qwen3": "qwen3-0.6b",
        "qwen3-0.6": "qwen3-0.6b",
        "phi1.5": "phi-1.5",
        "phi-1_5": "phi-1.5",
        "phi": "phi-1.5",
        "lfm2": "lfm2-1.2b",
        "lfm": "lfm2-1.2b",
        "lfm-1.2b": "lfm2-1.2b",
        "deepseek": "deepseek-coder-1.3b-base",
        "deepseek-coder": "deepseek-coder-1.3b-base",
        "deepseek-coder-1.3b": "deepseek-coder-1.3b-base",
        "deepseek-1.3b": "deepseek-coder-1.3b-base",
    }
    canonical_model = alias_map.get(model.lower(), model)

    target_url = url
    target_filename = None

    if canonical_model in models_data:
        m_cfg = models_data[canonical_model]
        target_url = target_url or m_cfg.get("download_url")
        gguf_path = m_cfg.get("gguf_path")
        if gguf_path:
            target_filename = Path(gguf_path).name

    if not target_url:
        console.print(f"[bold red]Error:[/bold red] No download URL configured for '{model}'.")
        console.print(f"Specify a direct URL using: [cyan]bench pull {model} --url <URL>[/cyan]")
        raise click.Abort()

    if not target_filename:
        target_filename = target_url.split("/")[-1].split("?")[0]
        if not target_filename.endswith(".gguf"):
            target_filename = f"{model}.gguf"

    dest_file = out_path / target_filename
    console.print(f"[bold cyan]Downloading {model}:[/bold cyan] {target_url}")
    console.print(f"[bold dim]Destination:[/bold dim] {dest_file}")

    import shutil
    import subprocess

    if shutil.which("curl"):
        try:
            # Use curl directly for fast, resumable streaming with progress bar
            cmd = ["curl", "-L", "-C", "-", "--progress-bar", "-o", str(dest_file), target_url]
            res = subprocess.run(cmd)
            if res.returncode != 0:
                raise RuntimeError(f"curl exited with code {res.returncode}")
            console.print(f"[bold green]✔ Successfully downloaded {dest_file.name} ({dest_file.stat().st_size / (1024*1024):.1f} MB)![/bold green]")
            console.print("To run the benchmark against this model:")
            console.print(f"  [cyan]bench run {model}[/cyan]")
            return
        except Exception as exc:
            console.print(f"[bold red]curl download failed:[/bold red] {exc}")
            raise click.Abort()

    # Fallback to urllib with custom User-Agent
    try:
        req = urllib.request.Request(
            target_url,
            headers={"User-Agent": "terminal-ai-bench/0.2.0 (Linux; x86_64)"},
        )
        with urllib.request.urlopen(req) as resp, open(dest_file, "wb") as f_out:
            total_size = int(resp.headers.get("Content-Length", 0))
            with Progress(
                TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                DownloadColumn(),
                "•",
                TransferSpeedColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task("download", filename=target_filename, total=total_size or None)
                chunk_size = 64 * 1024
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    progress.update(task_id, advance=len(chunk))

        console.print(f"[bold green]✔ Successfully downloaded {dest_file.name} ({dest_file.stat().st_size / (1024*1024):.1f} MB)![/bold green]")
        console.print("To run the benchmark against this model:")
        console.print(f"  [cyan]bench run {model}[/cyan]")
    except Exception as exc:
        console.print(f"[bold red]Download failed:[/bold red] {exc}")
        if dest_file.exists():
            dest_file.unlink()
        raise click.Abort()


@main.command(name="validate")
@click.option("--scenarios-dir", default="scenarios", help="Path to scenarios directory")
def validate_command(scenarios_dir: str):
    """Validate all YAML scenarios against the schema."""
    console = Console()
    try:
        scenarios = load_all_scenarios(scenarios_dir)
        console.print(f"[bold green]✔ Successfully validated {len(scenarios)} scenarios in '{scenarios_dir}'.[/bold green]")
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Domain", width=16)
        table.add_column("ID", width=18)
        table.add_column("Difficulty", width=14)
        table.add_column("Name")
        for s in scenarios:
            table.add_row(s.domain.value, s.id, s.difficulty.value, s.name)
        console.print(table)
    except Exception as exc:
        console.print(f"[bold red]Validation Failed:[/bold red] {exc}")
        raise click.Abort()


@main.command(name="list")
def list_command():
    """List configured models and available benchmark scenarios."""
    console = Console()
    runner = BenchmarkRunner()
    
    # Models table
    m_table = Table(title="Configured Models", show_header=True, header_style="bold magenta")
    m_table.add_column("Key", width=16)
    m_table.add_column("Name", width=22)
    m_table.add_column("Architecture", width=14)
    m_table.add_column("GGUF Path")
    for key, cfg in runner.models_config.items():
        m_table.add_row(key, cfg.get("name", ""), cfg.get("architecture", ""), cfg.get("gguf_path", "(in-memory)"))
    console.print(m_table)
    console.print()

    # Scenarios summary
    scenarios = load_all_scenarios(runner.scenarios_dir)
    s_table = Table(title="Available Scenarios", show_header=True, header_style="bold cyan")
    s_table.add_column("ID", width=18)
    s_table.add_column("Domain", width=16)
    s_table.add_column("Mode", width=12)
    s_table.add_column("Name")
    for s in scenarios:
        s_table.add_row(s.id, s.domain.value, s.mode.value, s.name)
    console.print(s_table)


@main.command(name="live")
@click.argument("model")
def live_command(model: str):
    """Run live host read-only inspection tests."""
    console = Console()
    console.print(f"[bold yellow]Executing live host read-only capabilities test...[/bold yellow]")
    tool_runtime = ToolRuntime(live_mode=True)
    
    # Run safe whitelisted tests across all host capability providers
    checks = [
        ToolRequest(provider="which", command="which", args=[]),
        ToolRequest(provider="bash_help", command="bash", args=["cd"]),
        ToolRequest(provider="man", command="pacman", args=[]),
        ToolRequest(provider="command_help", command="pacman", args=[]),
        ToolRequest(provider="package_info", command="pacman", args=["pacman"]),
        ToolRequest(provider="executable_info", command="ls", args=[]),
    ]
    for check in checks:
        res = tool_runtime.execute_request(check)
        status = "[green]SUCCESS[/green]" if res.success else "[yellow]SKIPPED/UNAVAILABLE[/yellow]"
        console.print(f"  Capability '{check.provider}' on '{check.command}': {status}")
    console.print("[bold green]✔ Live read-only inspection suite verified defensively.[/bold green]")


@main.command(name="export-failures")
@click.argument("model_or_run")
@click.option("--results-dir", default="results", help="Directory containing JSON run artifacts")
@click.option("--candidates-dir", default="training/candidates", help="Directory to export SFT candidates")
def export_failures_command(model_or_run: str, results_dir: str, candidates_dir: str):
    """Export failed benchmark scenarios into SFT training candidate records."""
    console = Console()
    res_path = Path(results_dir)
    out_dir = Path(candidates_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Find matching JSON result file
    target_file = None
    if Path(model_or_run).exists():
        target_file = Path(model_or_run)
    else:
        # Search results directory
        candidates = sorted(res_path.glob(f"{model_or_run}*.json"), reverse=True)
        if candidates:
            target_file = candidates[0]

    if not target_file or not target_file.exists():
        console.print(f"[bold red]Error:[/bold red] No result file found matching '{model_or_run}' in '{results_dir}'")
        raise click.Abort()

    with target_file.open("r", encoding="utf-8") as f:
        run_data = json.load(f)

    exported_count = 0
    scenarios = {s.id: s for s in load_all_scenarios("scenarios")}

    for s_result in run_data.get("scenarios", []):
        if not s_result.get("passed", False):
            s_id = s_result["scenario_id"]
            scenario = scenarios.get(s_id)
            if not scenario:
                continue

            candidate = {
                "scenario_id": s_id,
                "domain": s_result["domain"],
                "input": scenario.input.model_dump(),
                "context": scenario.context.model_dump(),
                "model_output": s_result.get("raw_response"),
                "scoring_failure_reasons": s_result.get("notes", []),
                "expected": scenario.expected.model_dump(),
                "model_metadata": {
                    "model": run_data.get("model"),
                    "benchmark_version": run_data.get("version"),
                    "timestamp": run_data.get("timestamp"),
                },
            }

            candidate_file = out_dir / f"{s_id}-{run_data.get('model')}.json"
            with candidate_file.open("w", encoding="utf-8") as out_f:
                json.dump(candidate, out_f, indent=2)
            exported_count += 1

    console.print(f"[bold green]✔ Exported {exported_count} failed scenarios to '{out_dir}'.[/bold green]")


@main.command(name="compare")
@click.argument("runs", nargs=-1, required=True)
@click.option("--results-dir", default="results", help="Directory containing results")
def compare_command(runs: List[str], results_dir: str):
    """Compare multiple model benchmark runs side-by-side."""
    console = Console()
    res_path = Path(results_dir)

    table = Table(title="Model Run Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Domain / Metric", style="dim", width=22)

    run_records = []
    for run_spec in runs:
        # Find file
        f = res_path / f"{run_spec}.json"
        if not f.exists():
            matched = list(res_path.glob(f"{run_spec}*.json"))
            if matched:
                f = matched[0]
        if not f.exists():
            console.print(f"[yellow]Warning: Could not find results for '{run_spec}'[/yellow]")
            continue

        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
            run_records.append(data)
            table.add_column(f"{data.get('model')} ({data.get('overall_score')}%)", justify="right", width=18)

    if not run_records:
        console.print("[bold red]No valid run records found to compare.[/bold red]")
        return

    domains = ["bash", "arch", "troubleshooting", "gcloud", "gh", "interaction", "safety"]
    for d in domains:
        row = [d.capitalize()]
        for r in run_records:
            score = r.get("domain_scores", {}).get(d, 0.0)
            row.append(f"{score:.1f}%")
        table.add_row(*row)

    table.add_section()
    table.add_row("Overall", *[f"{r.get('overall_score', 0.0):.1f}%" for r in run_records])
    console.print(table)


if __name__ == "__main__":
    main()
