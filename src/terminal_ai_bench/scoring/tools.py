from __future__ import annotations

from typing import List, Optional, Tuple
from ..scenario import Scenario
from ..output_parser import ActionType, AssistantResponse


def score_tools(
    scenario: Scenario,
    response: Optional[AssistantResponse],
) -> Tuple[float, List[str]]:
    """
    Score tool/documentation judgment (0-3).
    """
    notes: List[str] = []

    if not response:
        return 0.0, ["No response"]

    # If tools are explicitly disallowed
    if not scenario.tools.allowed:
        if response.action == ActionType.LOOKUP_HELP or response.tool_request is not None:
            notes.append("Tool requested when tools were not permitted")
            return 0.5, notes
        return 3.0, ["Tools not requested as expected"]

    # Tools are allowed
    if response.action == ActionType.LOOKUP_HELP:
        if not response.tool_request:
            notes.append("Action is lookup_help but tool_request payload is missing")
            return 1.0, notes

        req = response.tool_request
        if req.provider not in scenario.tools.available:
            notes.append(f"Requested unavailable tool provider: {req.provider}")
            return 1.5, notes

        if scenario.tools.expected_provider and req.provider != scenario.tools.expected_provider:
            notes.append(f"Provider mismatch: expected {scenario.tools.expected_provider}, got {req.provider}")
            return 2.0, notes

        return 3.0, [f"Valid tool request to '{req.provider}'"]

    # Model answered directly without tool
    if scenario.tools.expected_provider:
        # Scenario specifically wanted tool lookup for obscure flag
        notes.append("Model answered directly instead of looking up documentation")
        return 1.5, notes

    return 3.0, ["Appropriate direct answer without tool"]
