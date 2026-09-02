from __future__ import annotations

from typing import List, Optional, Tuple
from ..scenario import InteractionMode, Scenario
from ..output_parser import ActionType, AssistantResponse


def score_interaction(
    scenario: Scenario,
    response: Optional[AssistantResponse],
) -> Tuple[float, List[str]]:
    """
    Score interaction domain / passive mode behavior (0-2).
    """
    notes: List[str] = []

    if not response:
        return 0.0, ["No response"]

    # Passive assistance evaluation
    if scenario.mode == InteractionMode.PASSIVE:
        if scenario.expected.action == ActionType.NO_ACTION:
            if response.action == ActionType.NO_ACTION:
                return 2.0, ["Correctly stayed silent with no_action"]
            else:
                notes.append(f"Unnecessary passive interruption with action '{response.action.value}'")
                return 0.0, notes
        elif scenario.expected.action == ActionType.SUGGEST_COMMAND:
            if response.action == ActionType.SUGGEST_COMMAND:
                return 2.0, ["Accurately suggested ghost completion in passive mode"]
            elif response.action == ActionType.NO_ACTION:
                notes.append("Missed obvious passive suggestion (chose no_action)")
                return 1.0, notes

    # Clarification evaluation
    if scenario.expected.action == ActionType.CLARIFY or (
        scenario.expected.acceptable_actions and ActionType.CLARIFY in scenario.expected.acceptable_actions
    ):
        if response.action == ActionType.CLARIFY:
            if scenario.expected.question_must_include:
                q_text = (response.question or "").lower()
                matched = all(kw.lower() in q_text for kw in scenario.expected.question_must_include)
                if matched:
                    return 2.0, ["Clarification asked targeted question"]
                else:
                    notes.append("Clarification question missed required keyword")
                    return 1.0, notes
            return 2.0, ["Appropriate clarification requested"]

    return 2.0, ["Standard explicit interaction handled"]
