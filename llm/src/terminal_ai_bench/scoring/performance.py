from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PerformanceMetrics:
    model_load_time_s: float = 0.0
    ttft_ms: float = 0.0
    total_latency_ms: float = 0.0
    tokens_per_second: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    resident_ram_mb: float = 0.0
    peak_ram_mb: float = 0.0


def get_current_memory_mb() -> float:
    """Read current process resident memory (RSS) in megabytes."""
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except Exception:
        pass
    return 0.0
