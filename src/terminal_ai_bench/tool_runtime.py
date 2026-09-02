from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

from .output_parser import ToolRequest


class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    provider: str


class ToolRuntime:
    """Controlled read-only host capabilities provider."""

    ALLOWED_PROVIDERS = {
        "man",
        "command_help",
        "bash_help",
        "package_info",
        "executable_info",
        "which",
    }

    # Strict whitelist for live inspection binaries
    LIVE_WHITELIST = {
        "man",
        "bash",
        "pacman",
        "gh",
        "gcloud",
        "which",
        "type",
        "cat",
        "ls",
    }

    def __init__(self, fixtures_dir: Path | str = "fixtures", live_mode: bool = False):
        self.fixtures_dir = Path(fixtures_dir)
        self.live_mode = live_mode

    def execute_request(self, request: ToolRequest) -> ToolResult:
        """Execute a tool request safely either via deterministic fixture or live whitelist."""
        if request.provider not in self.ALLOWED_PROVIDERS:
            return ToolResult(
                success=False,
                output="",
                error=f"Provider '{request.provider}' is not allowed",
                provider=request.provider,
            )

        if not self.live_mode:
            return self._execute_deterministic(request)
        else:
            return self._execute_live(request)

    def _execute_deterministic(self, request: ToolRequest) -> ToolResult:
        """Search recorded fixtures in fixtures/ directory."""
        # Sanitize command name for file lookup
        cmd_slug = request.command.replace("/", "_").replace(" ", "_")
        
        # Check provider subdirectories
        candidates = [
            self.fixtures_dir / request.provider / f"{cmd_slug}.txt",
            self.fixtures_dir / request.command / f"{'-'.join(request.args)}-help.txt" if request.args else None,
            self.fixtures_dir / "help" / f"{cmd_slug}.txt",
            self.fixtures_dir / "man" / f"{cmd_slug}.txt",
        ]

        for candidate in candidates:
            if candidate and candidate.exists():
                content = candidate.read_text(encoding="utf-8")
                return ToolResult(
                    success=True,
                    output=content,
                    provider=request.provider,
                )

        return ToolResult(
            success=False,
            output="",
            error=f"No deterministic fixture found for provider '{request.provider}' and command '{request.command}'",
            provider=request.provider,
        )

    def _execute_live(self, request: ToolRequest) -> ToolResult:
        """
        Execute strictly whitelisted read-only host commands.
        CRITICAL SAFETY RULE: Never execute model commands. Only run hardcoded tool providers.
        """
        if request.command not in self.LIVE_WHITELIST:
            return ToolResult(
                success=False,
                output="",
                error=f"Command '{request.command}' is not in the live read-only whitelist",
                provider=request.provider,
            )

        # Build safe subprocess arguments defensively
        cmd_args: List[str] = []
        if request.provider == "man":
            cmd_args = ["man", "-P", "cat", request.command]
        elif request.provider == "bash_help":
            cmd_args = ["bash", "-c", f"help {' '.join(request.args)}"]
        elif request.provider == "command_help":
            # Only append --help to whitelisted binary
            cmd_args = [request.command] + request.args + ["--help"]
        elif request.provider == "package_info":
            cmd_args = ["pacman", "-Qi"] + request.args
        elif request.provider == "which":
            cmd_args = ["which", request.command]
        elif request.provider == "executable_info":
            import shlex
            cmd_args = ["bash", "-c", f"command -V {shlex.quote(request.command)}"]
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unsupported live provider '{request.provider}'",
                provider=request.provider,
            )

        try:
            res = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return ToolResult(
                success=(res.returncode == 0),
                output=res.stdout if res.returncode == 0 else res.stderr,
                error=res.stderr if res.returncode != 0 else None,
                provider=request.provider,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output="",
                error=f"Subprocess execution failed: {exc}",
                provider=request.provider,
            )
