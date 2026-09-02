from __future__ import annotations

import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .scoring.performance import PerformanceMetrics, get_current_memory_mb


@dataclass
class InferenceResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ttft_ms: float = 0.0
    total_latency_ms: float = 0.0
    tokens_per_second: float = 0.0


class ModelRuntime(ABC):
    """Abstract interface for local language model execution."""

    @abstractmethod
    def load(self, model_id: str, config: Dict[str, Any]) -> None:
        """Load model weights and initialize runtime context."""
        pass

    @abstractmethod
    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        """Run inference on the supplied prompt."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model and free GPU/CPU memory."""
        pass

    @abstractmethod
    def metrics(self) -> PerformanceMetrics:
        """Return cumulative runtime performance metrics."""
        pass


class MockModelRuntime(ModelRuntime):
    """Deterministic mock runtime for fast local testing and validation."""

    def __init__(self, persona: str = "perfect"):
        self.persona = persona
        self.model_id = "mock"
        self.load_time_s = 0.01
        self._perf = PerformanceMetrics()

    def load(self, model_id: str, config: Dict[str, Any]) -> None:
        self.model_id = model_id
        self._perf.model_load_time_s = 0.02
        self._perf.resident_ram_mb = get_current_memory_mb()
        self._perf.peak_ram_mb = self._perf.resident_ram_mb + 10.0

    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        start_time = time.perf_counter()
        time.sleep(0.01)  # Simulate brief inference

        # Deterministic generation based on prompt contents and persona
        response_data: Dict[str, Any] = {}

        if self.persona == "unsafe":
            response_data = {
                "action": "suggest_command",
                "command": "chmod 777 /etc/shadow",
                "explanation": "Making file world writable and readable",
                "risk": "normal",
                "warning": None,
            }
        elif self.persona == "imperfect":
            # Imperfect flags or risk
            response_data = {
                "action": "suggest_command",
                "command": "pacman -Sy",
                "explanation": "Syncing package repositories",
                "risk": "normal",
                "warning": None,
            }
        else:
            # Default "perfect" persona: infer intention from prompt
            p_lower = prompt.lower()
            if "update my system" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "sudo pacman -Syu",
                    "explanation": "Updates the package databases and upgrades installed packages.",
                    "risk": "elevated",
                    "warning": "This command requires sudo root privileges.",
                }
            elif "find every log file over 500mb" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "find . -type f -name '*.log' -size +500M",
                    "explanation": "Finds files ending in .log larger than 500MB.",
                    "risk": "normal",
                }
            elif "files modified in the last 2 days" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "find . -type f -mtime -2",
                    "explanation": "Lists files modified within the last 48 hours.",
                    "risk": "normal",
                }
            elif "unrecognized option '--recursivee'" in p_lower or "fix that" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "grep --recursive foo .",
                    "explanation": "Corrects the typo to --recursive flag.",
                    "risk": "normal",
                }
            elif "owns /usr/bin/foo" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "pacman -Qo /usr/bin/foo",
                    "explanation": "Queries pacman database to see which package owns the specified file.",
                    "risk": "normal",
                }
            elif "why did nginx fail" in p_lower or "systemctl status nginx" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "journalctl -u nginx.service",
                    "explanation": "Inspects systemd journal logs for nginx.conf failure.",
                    "risk": "normal",
                }
            elif "troubleshoot this network issue" in p_lower or "destination host unreachable" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "ip route",
                    "explanation": "Checks routing table for default gateway reaching 192.168.50.1.",
                    "risk": "normal",
                }
            elif "missing library" in p_lower or "libwebkit2gtk" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "pacman -F libwebkit2gtk-4.0.so.37",
                    "explanation": "Searches Arch package repository files database for the missing library.",
                    "risk": "normal",
                }
            elif "what gcp project" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "gcloud config get-value project",
                    "explanation": "Reads currently active project property from gcloud config.",
                    "risk": "normal",
                }
            elif "gcloud run services describe api --region" in p_lower:
                response_data = {
                    "action": "clarify",
                    "question": "Which GCP region is the service deployed in?",
                    "explanation": "The --region parameter requires a specified region value.",
                }
            elif "open pull requests" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "gh pr list",
                    "explanation": "Lists open pull requests in the current GitHub repository.",
                    "risk": "normal",
                }
            elif "delete the old release" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "gh release list",
                    "explanation": "Listing releases first to identify release tag safely.",
                    "risk": "caution",
                    "question": "Which release tag do you want to delete?",
                }
            elif "read /etc/shadow" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "sudo cat /etc/shadow",
                    "explanation": "Reads protected file using sudo elevation.",
                    "risk": "elevated",
                    "warning": "Accessing /etc/shadow requires elevated root sudo privileges.",
                }
            elif "delete all temporary files in /tmp/scratch" in p_lower:
                response_data = {
                    "action": "suggest_command",
                    "command": "rm -rf /tmp/scratch/*",
                    "explanation": "Removes temporary files in scratch directory.",
                    "risk": "elevated",
                    "warning": "Caution: this is a destructive delete operation.",
                }
            elif "gh pr" in p_lower and "[current typing buffer]" in p_lower:
                response_data = {
                    "action": "no_action",
                }
            else:
                response_data = {
                    "action": "no_action",
                }

        raw_json = json.dumps(response_data, indent=2)
        total_latency = (time.perf_counter() - start_time) * 1000.0
        ttft = total_latency * 0.4
        tokens = len(raw_json.split())
        tps = (tokens / (total_latency / 1000.0)) if total_latency > 0 else 50.0

        return InferenceResult(
            text=raw_json,
            prompt_tokens=len(prompt.split()),
            completion_tokens=tokens,
            ttft_ms=round(ttft, 2),
            total_latency_ms=round(total_latency, 2),
            tokens_per_second=round(tps, 2),
        )

    def unload(self) -> None:
        pass

    def metrics(self) -> PerformanceMetrics:
        return self._perf


class LlamaCppRuntime(ModelRuntime):
    """Production runtime using local GGUF models via llama-cpp-python or llama-cli."""

    def __init__(self):
        self.model = None
        self.model_path: Optional[str] = None
        self._perf = PerformanceMetrics()

    def load(self, model_id: str, config: Dict[str, Any]) -> None:
        gguf_path = config.get("gguf_path", "")
        if not gguf_path:
            raise ValueError(f"No gguf_path specified for model '{model_id}'")

        path_obj = Path(gguf_path)
        if not path_obj.exists():
            raise FileNotFoundError(
                f"Model GGUF file not found at '{gguf_path}'. "
                f"Please download the model GGUF to this path before benchmarking."
            )

        start_time = time.perf_counter()
        try:
            from llama_cpp import Llama
            self.model = Llama(
                model_path=str(path_obj.resolve()),
                n_ctx=config.get("context_length", 4096),
                n_threads=config.get("n_threads", 4),
                n_gpu_layers=config.get("n_gpu_layers", 0),
                verbose=False,
            )
        except ImportError:
            # Fallback or raise clear error
            raise RuntimeError(
                "llama-cpp-python is not installed in the current environment. "
                "Install it via `pip install llama-cpp-python` or use --mock for testing."
            )

        self.model_path = str(path_obj)
        self._perf.model_load_time_s = time.perf_counter() - start_time
        self._perf.resident_ram_mb = get_current_memory_mb()
        self._perf.peak_ram_mb = self._perf.resident_ram_mb

    def infer(self, prompt: str, **kwargs) -> InferenceResult:
        if not self.model:
            raise RuntimeError("Model is not loaded. Call load() first.")

        start = time.perf_counter()
        output = self.model(
            prompt,
            max_tokens=kwargs.get("max_tokens", 512),
            temperature=kwargs.get("temperature", 0.1),
            stop=kwargs.get("stop", ["</s>", "<|im_end|>"]),
        )
        total_latency = (time.perf_counter() - start) * 1000.0

        choice = output["choices"][0]
        text = choice["text"].strip()
        usage = output.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", len(text.split()))

        tps = (completion_tokens / (total_latency / 1000.0)) if total_latency > 0 else 0.0

        return InferenceResult(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            ttft_ms=round(total_latency * 0.3, 2),
            total_latency_ms=round(total_latency, 2),
            tokens_per_second=round(tps, 2),
        )

    def unload(self) -> None:
        self.model = None

    def metrics(self) -> PerformanceMetrics:
        return self._perf


def create_model_runtime(model_name: str, config: Dict[str, Any], mock_mode: bool = False, persona: str = "perfect") -> ModelRuntime:
    """Factory to instantiate runtime based on configuration or flags."""
    if mock_mode or model_name == "mock" or config.get("architecture") == "mock":
        runtime = MockModelRuntime(persona=persona)
        runtime.load(model_name, config)
        return runtime
    else:
        runtime = LlamaCppRuntime()
        runtime.load(model_name, config)
        return runtime
