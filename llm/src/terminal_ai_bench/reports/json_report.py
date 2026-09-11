from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..scoring import ScenarioScore
from ..privacy import sanitize


def generate_json_report(
    model_name: str,
    overall_score: float,
    domain_scores: Dict[str, float],
    category_scores: Dict[str, float],
    perf_metrics: Dict[str, Any],
    scenario_scores: List[ScenarioScore],
    output_path: Path | str,
    model_sha256: Optional[str] = None,
    evaluation_mode: str = "raw",
    system_metrics: Optional[Dict[str, Any]] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Path:
    """Serialize full benchmark run into structured JSON."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    report_data = {
        "benchmark": "terminal-ai-bench",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_mode": evaluation_mode,
        "implementation": "python-reference-only; does not certify desktop staging",
        "holdout_status": "examined regression data; not an unseen holdout",
        "provenance": provenance,
        "ttft_note": "Non-streaming live TTFT is unmeasured (0 sentinel); mock timings are synthetic",
        "model": model_name,
        "model_sha256": model_sha256,
        "overall_score": round(overall_score, 2),
        "domain_scores": domain_scores,
        "capability_scores": category_scores,
        "performance": perf_metrics,
        "system_metrics": system_metrics,
        "scenarios": [s.model_dump() for s in scenario_scores],
    }

    with out.open("w", encoding="utf-8") as f:
        json.dump(sanitize(report_data), f, indent=2)

    return out
