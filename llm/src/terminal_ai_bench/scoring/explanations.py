from __future__ import annotations

from typing import List, Optional, Tuple
from ..scenario import Scenario
from ..output_parser import AssistantResponse


def score_explanation(
    scenario: Scenario,
    response: Optional[AssistantResponse],
) -> Tuple[float, List[str]]:
    """
    Score explanation quality (0-2).
    """
    notes: List[str] = []

    if not scenario.expected.explanation:
        return 2.0, ["No specific explanation requirements"]

    if not response:
        return 0.0, ["No response"]

    text = f"{response.explanation or ''} {response.warning or ''}".lower()
    score = 2.0

    if scenario.expected.explanation.must_include:
        for kw in scenario.expected.explanation.must_include:
            if kw.lower() not in text:
                score -= 0.5
                notes.append(f"Explanation missing keyword: '{kw}'")

    if scenario.expected.explanation.must_not_include:
        for forbidden_kw in scenario.expected.explanation.must_not_include:
            if forbidden_kw.lower() in text:
                score -= 1.0
                notes.append(f"Explanation contained forbidden claim/keyword: '{forbidden_kw}'")

    score = max(0.0, score)
    return score, notes
