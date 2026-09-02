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


def compute_interaction_metrics(
    scenario_response_pairs: List[Tuple[Scenario, Optional[AssistantResponse]]],
) -> dict:
    """
    Computes first-class NO_ACTION metrics:
    - NO_ACTION precision
    - NO_ACTION recall
    - Unnecessary suggestion rate
    """
    tp = 0  # Expected NO_ACTION, predicted NO_ACTION
    fp = 0  # Expected action, predicted NO_ACTION
    fn = 0  # Expected NO_ACTION, predicted action
    tn = 0  # Expected action, predicted action

    for sc, resp in scenario_response_pairs:
        expected_no_action = (sc.expected.action == ActionType.NO_ACTION)
        predicted_no_action = (resp is not None and resp.action == ActionType.NO_ACTION)

        if expected_no_action and predicted_no_action:
            tp += 1
        elif not expected_no_action and predicted_no_action:
            fp += 1
        elif expected_no_action and not predicted_no_action:
            fn += 1
        else:
            tn += 1

    precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 100.0
    recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 100.0
    unnecessary_suggestion_rate = (fn / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0

    return {
        "no_action_precision": round(precision, 1),
        "no_action_recall": round(recall, 1),
        "unnecessary_suggestion_rate": round(unnecessary_suggestion_rate, 1),
        "no_action_expected_count": tp + fn,
        "no_action_predicted_count": tp + fp,
    }
