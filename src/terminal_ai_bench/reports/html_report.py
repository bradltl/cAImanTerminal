from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..scoring import ScenarioScore


def generate_html_report(
    model_name: str,
    overall_score: float,
    domain_scores: Dict[str, float],
    category_scores: Dict[str, float],
    perf_metrics: Dict[str, Any],
    scenario_scores: List[ScenarioScore],
    output_path: Path | str,
    model_sha256: Optional[str] = None,
) -> Path:
    """Generate interactive, standalone HTML benchmark report."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    sha_badge = f"<p style='color: #a6adc8; font-family: monospace; font-size: 12px; margin: 4px 0 0 0;'>SHA-256: {html.escape(model_sha256)}</p>" if model_sha256 else ""

    domain_rows = "".join(
        f"<tr><td>{html.escape(k.capitalize())}</td><td><b>{v:.1f}%</b></td></tr>"
        for k, v in domain_scores.items()
    )

    cap_rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td><b>{v:.1f}%</b></td></tr>"
        for k, v in category_scores.items()
    )

    scenario_cards = ""
    for s in scenario_scores:
        status_color = "#22c55e" if s.passed else "#ef4444"
        badge = "PASS" if s.passed else "FAIL"
        notes_html = "".join(f"<li>{html.escape(n)}</li>" for n in s.notes)
        scenario_cards += f"""
        <div class="card" style="border-left: 5px solid {status_color}; margin-bottom: 12px; padding: 12px; background: #1e1e2e; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4>[{html.escape(s.domain.value)}] {html.escape(s.scenario_id)}: {html.escape(s.scenario_name)}</h4>
                <span style="background: {status_color}; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;">{badge} ({s.percentage:.1f}%)</span>
            </div>
            <div style="margin-top: 8px; font-size: 13px; color: #a6adc8;">
                <div><b>Command:</b> <code>{html.escape(s.parsed_command or 'None')}</code></div>
                <div><b>Score Breakdown:</b> Cmd: {s.command_score}/4 | Flag: {s.flag_score}/3 | Risk: {s.risk_score}/2 | Tool: {s.tool_score}/3 | Context: {s.context_score}/2 | Expl: {s.explanation_score}/2 | Format: {s.format_compliance}/1</div>
                <ul style="margin-top: 4px; padding-left: 20px;">{notes_html}</ul>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>terminal-ai-bench - {html.escape(model_name)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #181825; color: #cdd6f4; margin: 0; padding: 24px; }}
        h1, h2, h3, h4 {{ color: #cdd6f4; margin: 0 0 10px 0; }}
        .header {{ border-bottom: 2px solid #313244; padding-bottom: 16px; margin-bottom: 24px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; background: #1e1e2e; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #313244; }}
        th {{ background: #313244; color: #89b4fa; }}
        code {{ background: #313244; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #a6e3a1; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>terminal-ai-bench</h1>
        <h3>Model: {html.escape(model_name)} | Overall Score: <span style="color: #89b4fa;">{overall_score:.1f}%</span></h3>
        <p style="color: #6c7086; margin: 0;">Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        {sha_badge}
    </div>

    <div class="grid">
        <div>
            <h2>Domain Scores</h2>
            <table>
                <tr><th>Domain</th><th>Score</th></tr>
                {domain_rows}
            </table>
        </div>
        <div>
            <h2>Diagnostic Capabilities</h2>
            <table>
                <tr><th>Capability</th><th>Score</th></tr>
                {cap_rows}
            </table>
        </div>
    </div>

    <h2>Scenario Evaluation Details</h2>
    <div>
        {scenario_cards}
    </div>
</body>
</html>
"""

    with out.open("w", encoding="utf-8") as f:
        f.write(html_content)

    return out
