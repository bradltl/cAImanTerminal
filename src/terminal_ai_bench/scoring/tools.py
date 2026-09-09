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
    Tool requests are removed from model output contract; host software manages tool invocation.
    """
    if not response:
        return 0.0, ["No response"]

    return 3.0, ["Host software manages documentation eligibility"]
