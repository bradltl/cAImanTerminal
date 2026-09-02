from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from .output_parser import ActionType, RiskLevel


class Domain(str, Enum):
    BASH = "bash"
    ARCH = "arch"
    TROUBLESHOOTING = "troubleshooting"
    GCLOUD = "gcloud"
    GH = "gh"
    INTERACTION = "interaction"
    SAFETY = "safety"


class Difficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class InteractionMode(str, Enum):
    EXPLICIT = "explicit"
    PASSIVE = "passive"


class OSInfo(BaseModel):
    id: str = "cachyos"
    base: str = "arch"


class Context(BaseModel):
    os: OSInfo = Field(default_factory=OSInfo)
    shell: str = "bash"
    cwd: str = "/home/testuser"
    env: Dict[str, str] = Field(default_factory=dict)


class HistoryTurn(BaseModel):
    command: str
    exit_code: int = 0
    output: str = ""


class TypingInfo(BaseModel):
    idle_ms: int = 650


class MatchRule(BaseModel):
    type: str = "exact"  # exact, regex, structured
    value: Optional[str] = None
    executable: Optional[str] = None
    flags: Optional[Dict[str, List[str]]] = None  # e.g. {"contains": ["-size"]}
    arguments: Optional[Dict[str, List[str]]] = None  # e.g. {"contains": ["+500M"]}


class CommandExpectation(BaseModel):
    match: MatchRule


class TextConstraint(BaseModel):
    must_include: List[str] = Field(default_factory=list)
    must_not_include: List[str] = Field(default_factory=list)


class Expected(BaseModel):
    action: Optional[ActionType] = None
    acceptable_actions: Optional[List[ActionType]] = None
    commands: Optional[List[CommandExpectation]] = None
    risk: Optional[RiskLevel] = None
    explanation: Optional[TextConstraint] = None
    warnings: Optional[TextConstraint] = None
    question_must_include: Optional[List[str]] = None


class Forbidden(BaseModel):
    command_patterns: List[str] = Field(default_factory=list)
    behaviors: List[str] = Field(default_factory=list)
    claims: List[str] = Field(default_factory=list)


class ToolConfig(BaseModel):
    allowed: bool = False
    available: List[str] = Field(default_factory=list)
    expected_provider: Optional[str] = None


class ScenarioInput(BaseModel):
    text: str
    cursor_position: Optional[int] = None


class ScenarioTurn(BaseModel):
    turn_index: int = 1
    input: ScenarioInput
    typing: Optional[TypingInfo] = None
    expected: Expected = Field(default_factory=Expected)
    forbidden: Forbidden = Field(default_factory=Forbidden)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    simulated_command: Optional[str] = None
    simulated_output: Optional[str] = None
    simulated_exit_code: int = 0


class Scenario(BaseModel):
    id: str
    name: str
    domain: Domain
    difficulty: Difficulty = Difficulty.BASIC
    mode: InteractionMode = InteractionMode.EXPLICIT
    context: Context = Field(default_factory=Context)
    history: List[HistoryTurn] = Field(default_factory=list)
    input: Optional[ScenarioInput] = None
    typing: Optional[TypingInfo] = None
    expected: Expected = Field(default_factory=Expected)
    forbidden: Forbidden = Field(default_factory=Forbidden)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    turns: List[ScenarioTurn] = Field(default_factory=list)
    file_path: Optional[str] = None


def load_scenario(path: Path | str) -> Scenario:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Scenario file not found: {path_obj}")
    with path_obj.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Scenario content must be a YAML mapping, got: {type(data)}")
    scenario = Scenario.model_validate(data)
    scenario.file_path = str(path_obj.resolve())
    return scenario


def load_all_scenarios(scenarios_dir: Path | str) -> List[Scenario]:
    base_dir = Path(scenarios_dir)
    scenarios: List[Scenario] = []
    for yaml_file in sorted(base_dir.rglob("*.yaml")):
        try:
            scenarios.append(load_scenario(yaml_file))
        except Exception as exc:
            raise RuntimeError(f"Error loading scenario from {yaml_file}: {exc}") from exc
    return scenarios
