from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    NO_ACTION = "no_action"
    SUGGEST_COMMAND = "suggest_command"
    SUGGEST_SEQUENCE = "suggest_sequence"
    LOOKUP_HELP = "lookup_help"
    EXPLAIN = "explain"
    CLARIFY = "clarify"


class RiskLevel(str, Enum):
    NORMAL = "normal"
    CAUTION = "caution"
    ELEVATED = "elevated"


from pydantic import BaseModel, Field, field_validator


class ToolRequest(BaseModel):
    provider: str
    command: str
    args: Optional[List[str]] = Field(default_factory=list)

    @field_validator("args", mode="before")
    @classmethod
    def normalize_args(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class AssistantResponse(BaseModel):
    action: ActionType
    command: Optional[str] = None
    commands: Optional[List[str]] = None
    explanation: Optional[str] = None
    risk: Optional[RiskLevel] = None
    warning: Optional[str] = None
    question: Optional[str] = None
    tool_request: Optional[ToolRequest] = None


class ParseResult(BaseModel):
    success: bool
    response: Optional[AssistantResponse] = None
    raw_text: str
    cleaned_json_text: Optional[str] = None
    error: Optional[str] = None
    format_compliance: float = 0.0


def extract_json_candidate(text: str) -> str:
    """Extract candidate JSON string from raw model output."""
    text = text.strip()
    # Check for markdown code blocks: ```json ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # Try finding the first '{' and last '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()
    
    return text


def parse_response(raw_text: str) -> ParseResult:
    """Parse raw model output into validated AssistantResponse."""
    cleaned = extract_json_candidate(raw_text)
    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            return ParseResult(
                success=False,
                raw_text=raw_text,
                cleaned_json_text=cleaned,
                error="Extracted JSON is not a dictionary object",
                format_compliance=0.0,
            )
        
        # Normalize action case if needed
        if "action" in data and isinstance(data["action"], str):
            data["action"] = data["action"].strip().lower()
        if "risk" in data and isinstance(data["risk"], str):
            data["risk"] = data["risk"].strip().lower()
        
        response = AssistantResponse.model_validate(data)
        return ParseResult(
            success=True,
            response=response,
            raw_text=raw_text,
            cleaned_json_text=cleaned,
            format_compliance=1.0,
        )
    except json.JSONDecodeError as exc:
        return ParseResult(
            success=False,
            raw_text=raw_text,
            cleaned_json_text=cleaned,
            error=f"JSON decode error: {exc}",
            format_compliance=0.0,
        )
    except Exception as exc:
        return ParseResult(
            success=False,
            raw_text=raw_text,
            cleaned_json_text=cleaned,
            error=f"Schema validation error: {exc}",
            format_compliance=0.5,  # Valid JSON but failed schema
        )
