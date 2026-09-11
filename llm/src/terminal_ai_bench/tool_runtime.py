from __future__ import annotations

from pathlib import Path
from typing import Optional
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

    def __init__(self, fixtures_dir: Path | str = "fixtures", live_mode: bool = False):
        self.fixtures_dir = Path(fixtures_dir)
        self.live_mode = live_mode
        if live_mode:
            raise ValueError("Python reference tools are fixture-only; use Rust's fixed documentation routes for live inspection")

    def execute_request(self, request: ToolRequest) -> ToolResult:
        """Read a bounded fixture; live reference tools are intentionally disabled."""
        if self.live_mode or request.provider not in self.ALLOWED_PROVIDERS:
            return ToolResult(
                success=False,
                output="",
                error=f"Provider '{request.provider}' is not allowed",
                provider=request.provider,
            )

        return self._execute_deterministic(request)

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
            if candidate and candidate.resolve().is_relative_to(self.fixtures_dir.resolve()) and candidate.is_file():
                with candidate.open(encoding="utf-8") as fixture:
                    content = fixture.read(65537)
                if len(content) > 65536:
                    continue
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
