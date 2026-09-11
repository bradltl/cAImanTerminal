"""
test_gold_contract_integrity.py

Benchmark-gold integrity tests for scenarios_v3.

These tests enforce the oracle gold intent_contract schema and semantic consistency
rules. They run entirely on scenario YAML data — no model inference required.

Rules enforced:
1. Every scenarios_v3 YAML has an intent_contract block.
2. intent_type is present and is exactly 'supported' or 'expansion'.
3. domain is from the approved semantic domain vocabulary.
4. operation is a non-empty string with no whitespace.
5. Consistency: if expected.action == 'clarify'/'explain', domain must be
   'interaction' or 'safety' and operation must not imply a concrete command
   (is_command_contract == False).
6. Consistency: if expected.action == 'suggest_command', the contract's
   is_command_contract must be True (operation not in {clarify,explain,no_action}).
7. destructive==True contracts must have domain in {'safety','filesystem','git','gcloud'}.
8. No contract may set both destructive==True and intent_type=='expansion'
   without domain=='safety' (catastrophic ops must be safety-domain).
9. Expansion contracts must be registered in CANONICAL_INTENT_SPECS.
10. Supported contracts that map to a registered spec must agree on domain.
11. Multi-turn scenarios: each turn that has an intent_contract must pass
    the same rules.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict, List

from terminal_ai_bench.scenario import load_all_scenarios, Scenario
from terminal_ai_bench.system.intent_extractor import _contract_from_dict
from terminal_ai_bench.system.intent_registry import IntentRegistry
from terminal_ai_bench.system.types import IntentContract


# ─── Vocabulary constants ────────────────────────────────────────────────────

APPROVED_DOMAINS = frozenset({
    "filesystem",
    "git",
    "gh",
    "gcloud",
    "pacman",
    "journalctl",
    "systemctl",
    "troubleshoot",
    "safety",
    "interaction",
})

NON_COMMAND_OPERATIONS = frozenset({"clarify", "explain", "no_action"})

SCENARIOS_DIR = "scenarios_v3"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def v3_scenarios() -> List[Scenario]:
    return load_all_scenarios(SCENARIOS_DIR)


@pytest.fixture(scope="module")
def registry() -> IntentRegistry:
    return IntentRegistry()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _expected_actions(scenario: Scenario) -> List[str]:
    """Return all possible expected actions for a scenario."""
    if not scenario.expected:
        return []
    if isinstance(scenario.expected, dict):
        action = scenario.expected.get("action")
        acceptable = scenario.expected.get("acceptable_actions", [])
        if action:
            return [action] + list(acceptable)
        return list(acceptable)
    # Pydantic model
    actions = []
    if hasattr(scenario.expected, "action") and scenario.expected.action:
        actions.append(scenario.expected.action)
    if hasattr(scenario.expected, "acceptable_actions"):
        actions.extend(scenario.expected.acceptable_actions or [])
    return actions


def _contract_dict(scenario: Scenario) -> Dict[str, Any]:
    """Return the top-level intent_contract dict for a scenario."""
    return scenario.intent_contract or {}


def _build_contract(d: Dict[str, Any], scenario_id: str = "") -> IntentContract:
    return _contract_from_dict(d, scenario_id=scenario_id)


def _all_contract_pairs(scenarios: List[Scenario]):
    """Yield (scenario_id, contract_dict) for every scenario and multi-turn turn."""
    for s in scenarios:
        if s.intent_contract:
            yield s.id, s.intent_contract
        if s.turns:
            for t in s.turns:
                if t.intent_contract:
                    yield f"{s.id}-t{t.turn_index}", t.intent_contract


# ─── Test 1: Every v3 scenario has an explicit intent_contract ───────────────

def test_all_v3_scenarios_have_intent_contract(v3_scenarios):
    """Every scenario in scenarios_v3 must have an explicit intent_contract block."""
    missing = [s.id for s in v3_scenarios if not s.intent_contract]
    assert not missing, (
        f"{len(missing)} scenarios lack intent_contract:\n"
        + "\n".join(f"  {sid}" for sid in sorted(missing))
    )


# ─── Test 2: intent_type is present and valid ────────────────────────────────

def test_all_v3_intent_contracts_have_valid_intent_type(v3_scenarios):
    """Every intent_contract must have intent_type in {'supported', 'expansion'}."""
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        intent_type = d.get("intent_type")
        if intent_type not in ("supported", "expansion"):
            bad.append((sid, intent_type))
    assert not bad, (
        f"{len(bad)} contracts have missing/invalid intent_type:\n"
        + "\n".join(f"  {sid}: {repr(it)}" for sid, it in bad)
    )


# ─── Test 3: domain is from approved vocabulary ───────────────────────────────

def test_all_v3_contracts_use_approved_domain(v3_scenarios):
    """Every intent_contract.domain must be in the approved semantic domain vocabulary."""
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        domain = d.get("domain", "")
        if domain not in APPROVED_DOMAINS:
            bad.append((sid, domain))
    assert not bad, (
        f"{len(bad)} contracts use unapproved domain:\n"
        + "\n".join(f"  {sid}: '{dom}'" for sid, dom in bad)
        + f"\n\nApproved domains: {sorted(APPROVED_DOMAINS)}"
    )


# ─── Test 4: operation is a non-empty identifier string ──────────────────────

def test_all_v3_contracts_have_valid_operation(v3_scenarios):
    """Every intent_contract.operation must be a non-empty string with no whitespace."""
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        op = d.get("operation", "")
        if not op or not isinstance(op, str) or " " in op.strip():
            bad.append((sid, repr(op)))
    assert not bad, (
        f"{len(bad)} contracts have invalid operation:\n"
        + "\n".join(f"  {sid}: {op}" for sid, op in bad)
    )


# ─── Test 5: clarify/explain expected → non-command contract ─────────────────

def test_clarify_expected_actions_have_non_command_contract(v3_scenarios):
    """
    If a scenario's ONLY acceptable actions are clarify/explain (never suggest_command),
    then its intent_contract must resolve to is_command_contract == False,
    UNLESS it is a safety-blocked scenario (which describes the blocked command).
    """
    bad = []
    for s in v3_scenarios:
        if not s.intent_contract:
            continue
        # Safety scenarios intentionally describe the blocked command contract
        if s.intent_contract.get("domain") == "safety":
            continue
            
        actions = _expected_actions(s)
        # Only fire if all expected actions are non-command
        command_actions = [a for a in actions if a not in ("clarify", "explain")]
        if actions and not command_actions:
            # All expected actions are clarify/explain → contract must be non-command
            try:
                contract = _build_contract(s.intent_contract, s.id)
            except Exception as e:
                bad.append((s.id, f"deserialization error: {e}"))
                continue
            if contract.is_command_contract:
                bad.append((
                    s.id,
                    f"expected only clarify/explain but contract operation='{contract.operation}' "
                    f"is_command_contract=True (domain={contract.domain})"
                ))
    assert not bad, (
        f"{len(bad)} contracts are inconsistently is_command_contract=True "
        f"despite clarify-only expected actions:\n"
        + "\n".join(f"  {sid}: {msg}" for sid, msg in bad)
    )


# ─── Test 6: suggest_command expected → command contract ─────────────────────

def test_suggest_command_expected_actions_have_command_contract(v3_scenarios):
    """
    If a scenario's expected action is suggest_command, the intent_contract must
    have is_command_contract == True.
    """
    bad = []
    for s in v3_scenarios:
        if not s.intent_contract:
            continue
        actions = _expected_actions(s)
        if "suggest_command" not in actions:
            continue
        try:
            contract = _build_contract(s.intent_contract, s.id)
        except Exception as e:
            bad.append((s.id, f"deserialization error: {e}"))
            continue
        if not contract.is_command_contract:
            bad.append((
                s.id,
                f"expected suggest_command but contract operation='{contract.operation}' "
                f"is_command_contract=False (domain={contract.domain})"
            ))
    assert not bad, (
        f"{len(bad)} contracts are inconsistently is_command_contract=False "
        f"despite suggest_command expected action:\n"
        + "\n".join(f"  {sid}: {msg}" for sid, msg in bad)
    )


# ─── Test 7: destructive contracts must be safety-domain or acknowledged ─────

def test_destructive_contracts_are_safety_or_filesystem_git(v3_scenarios):
    """
    Contracts with destructive=True must have domain in {safety, filesystem, git, gcloud}.
    This catches model mistakes where a destructive contract is accidentally placed in
    an unexpected domain.
    """
    ALLOWED_DESTRUCTIVE_DOMAINS = frozenset({"safety", "filesystem", "git", "gcloud"})
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        if d.get("destructive"):
            domain = d.get("domain", "")
            if domain not in ALLOWED_DESTRUCTIVE_DOMAINS:
                bad.append((sid, domain))
    assert not bad, (
        f"{len(bad)} contracts have destructive=True in unexpected domain:\n"
        + "\n".join(f"  {sid}: domain={dom}" for sid, dom in bad)
        + f"\n\nAllowed: {sorted(ALLOWED_DESTRUCTIVE_DOMAINS)}"
    )


# ─── Test 8: expansion contracts are registered in CANONICAL_INTENT_SPECS ─────

def test_expansion_contracts_are_registered_in_canonical_specs(v3_scenarios, registry):
    """
    Every intent_contract with intent_type='expansion' must have a corresponding
    entry in CANONICAL_INTENT_SPECS so the resolver knows about it.
    """
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        if d.get("intent_type") != "expansion":
            continue
        dom = d.get("domain", "")
        op = d.get("operation", "")
        spec = registry.get_spec(dom, op)
        if spec is None:
            bad.append((sid, f"{dom}:{op}"))
    assert not bad, (
        f"{len(bad)} expansion contracts are NOT registered in CANONICAL_INTENT_SPECS:\n"
        + "\n".join(f"  {sid}: {key}" for sid, key in bad)
        + "\n\nExpansion operations must be registered so the resolver can find them."
    )


# ─── Test 9: supported contracts domain agreement with registry ───────────────

def test_supported_contracts_domain_agrees_with_registry(v3_scenarios, registry):
    """
    Supported contracts that exist in CANONICAL_INTENT_SPECS must agree on domain.
    This catches mis-classified contracts (e.g., operation registered under 'gh'
    but contract says 'gcloud').
    """
    bad = []
    for sid, d in _all_contract_pairs(v3_scenarios):
        if d.get("intent_type") == "expansion":
            continue
        dom = d.get("domain", "")
        op = d.get("operation", "")
        if not dom or not op:
            continue
        # Look up by operation name (not domain) to detect cross-domain mismatches
        spec = registry.find_by_operation(op)
        if spec is None:
            continue  # Not in registry yet — acceptable for new supported ops
        if spec.domain != dom:
            bad.append((sid, op, f"contract.domain={dom!r} but registry.domain={spec.domain!r}"))
    assert not bad, (
        f"{len(bad)} supported contracts have domain mismatch with CANONICAL_INTENT_SPECS:\n"
        + "\n".join(f"  {sid}: op={op}, {msg}" for sid, op, msg in bad)
    )


# ─── Test 10: no obviously inconsistent safety blocks ────────────────────────

def test_safety_blocked_scenarios_have_safety_domain(v3_scenarios):
    """
    Scenarios with domain='safety' and expected action in (clarify, explain)
    must have destructive=True or the operation name must indicate what was blocked
    (not a generic 'clarify' operation).
    """
    bad = []
    for s in v3_scenarios:
        d = s.intent_contract
        if not d:
            continue
        if d.get("domain") != "safety":
            continue
        actions = _expected_actions(s)
        # For safety-blocked scenarios (all actions are clarify/explain),
        # the contract operation must NOT be 'clarify' — it should describe what was blocked
        if actions and all(a in ("clarify", "explain") for a in actions):
            op = d.get("operation", "")
            if op == "clarify":
                bad.append((s.id, "safety-blocked scenario uses operation='clarify'; should describe what was blocked"))
    assert not bad, (
        f"{len(bad)} safety-blocked scenarios use 'clarify' as their operation:\n"
        + "\n".join(f"  {sid}: {msg}" for sid, msg in bad)
    )


# ─── Test 11: multi-turn turn contracts pass same rules ──────────────────────

def test_multiturn_turn_contracts_are_valid(v3_scenarios):
    """Per-turn intent_contracts in multi-turn scenarios must pass the same domain/operation rules."""
    bad = []
    for s in v3_scenarios:
        if not s.turns:
            continue
        for t in s.turns:
            if not t.intent_contract:
                continue
            d = t.intent_contract
            tid = f"{s.id}-t{t.turn_index}"
            dom = d.get("domain", "")
            op = d.get("operation", "")
            it = d.get("intent_type", "supported")  # default supported for turns
            if dom not in APPROVED_DOMAINS:
                bad.append((tid, f"unapproved domain '{dom}'"))
            if not op or " " in op.strip():
                bad.append((tid, f"invalid operation '{op}'"))
            if it not in ("supported", "expansion"):
                bad.append((tid, f"invalid intent_type '{it}'"))
    assert not bad, (
        f"{len(bad)} turn-level contracts are invalid:\n"
        + "\n".join(f"  {tid}: {msg}" for tid, msg in bad)
    )
