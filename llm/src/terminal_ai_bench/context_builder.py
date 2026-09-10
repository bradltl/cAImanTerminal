from __future__ import annotations

from pathlib import Path
from typing import Optional
from .scenario import InteractionMode, Scenario


class ContextBuilder:
    def __init__(self, prompts_dir: Path | str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self.system_prompt = self._load_template("system.txt")
        self.explicit_template = self._load_template("explicit.txt")
        self.passive_template = self._load_template("passive.txt")
        self.error_template = self._load_template("error.txt")

    def _load_template(self, filename: str) -> str:
        path = self.prompts_dir / filename
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def format_history(self, scenario: Scenario) -> str:
        if not scenario.history:
            return "(No recent history)"
        lines = []
        for turn in scenario.history:
            lines.append(f"$ {turn.command}")
            if turn.output:
                lines.append(turn.output.strip())
            lines.append(f"[Exit code: {turn.exit_code}]")
        return "\n".join(lines)

    def build_prompt(self, scenario: Scenario) -> str:
        history_str = self.format_history(scenario)
        os_info = scenario.context.os

        # Check if the scenario has a recent failed command in history
        last_turn = scenario.history[-1] if scenario.history else None
        has_error = last_turn is not None and last_turn.exit_code != 0

        if scenario.mode == InteractionMode.PASSIVE:
            idle_ms = scenario.typing.idle_ms if scenario.typing else 650
            user_part = self.passive_template.format(
                os_id=os_info.id,
                os_base=os_base if (os_base := os_info.base) else "linux",
                shell=scenario.context.shell,
                cwd=scenario.context.cwd,
                history=history_str,
                idle_ms=idle_ms,
                input_text=scenario.input.text,
            )
        elif has_error and scenario.domain.value in ("troubleshooting", "arch") and self.error_template:
            user_part = self.error_template.format(
                os_id=os_info.id,
                os_base=os_info.base,
                shell=scenario.context.shell,
                cwd=scenario.context.cwd,
                failed_command=last_turn.command,
                exit_code=last_turn.exit_code,
                error_output=last_turn.output,
                input_text=scenario.input.text,
            )
        else:
            user_part = self.explicit_template.format(
                os_id=os_info.id,
                os_base=os_info.base,
                shell=scenario.context.shell,
                cwd=scenario.context.cwd,
                history=history_str,
                input_text=scenario.input.text,
            )

        full_prompt = f"{self.system_prompt}\n\n{user_part}"
        return full_prompt
