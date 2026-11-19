"""Tests for self-correction feedback loop, edge decision matrix, and hard ceiling guard."""

import pytest
from src.graph.state import create_initial_state
from src.graph.edges import (
    route_review_verdict,
    route_revision_target,
    route_after_destination,
)
from src.models.review import ReviewResult


def test_route_review_verdict_approved_passes_to_synthesis():
    state = create_initial_state("Trip")
    state["review_result"] = ReviewResult(
        approved=True,
        violations=[],
        iteration=1,
    )
    verdict = route_review_verdict(state)
    assert verdict == "synthesize_final_plan_node"


def test_route_review_verdict_violations_routes_to_dispatcher():
    state = create_initial_state("Trip")
    state["revision_count"] = 1
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["OVER_BUDGET: AED 300 over limit"],
        iteration=1,
    )
    verdict = route_review_verdict(state)
    assert verdict == "revision_dispatcher_node"


def test_route_review_verdict_hard_ceiling_forces_synthesis():
    state = create_initial_state("Trip")
    # Reach 3 iterations ceiling
    state["revision_count"] = 3
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["OVER_BUDGET: persistently over budget"],
        iteration=3,
    )
    verdict = route_review_verdict(state)
    assert verdict == "synthesize_final_plan_node"
    assert any("ceiling" in msg for msg in state["error_log"])


def test_route_revision_target_prioritizes_correct_nodes():
    state = create_initial_state("Trip")

    # 1. Budget violation
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["OVER_BUDGET: AED 500 over limit", "PACE_EXCEEDED: Day 1"],
    )
    assert route_revision_target(state) == "budget_calculator_node"

    # 2. Pacing violation
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["PACE_EXCEEDED: Day 2 active hours > 8.5h"],
    )
    assert route_revision_target(state) == "logistics_routing_node"

    # 3. Transit violation
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["EXCESSIVE_TRANSIT: Day 1 transit > 45m"],
    )
    assert route_revision_target(state) == "logistics_routing_node"

    # 4. Preference omission
    state["review_result"] = ReviewResult(
        approved=False,
        violations=["PREFERENCE_OMISSION: Missing beach activity"],
    )
    assert route_revision_target(state) == "destination_research_node"


def test_route_after_destination():
    # Initial run (revision_count == 0)
    state = create_initial_state("Initial test")
    state["revision_count"] = 0
    assert route_after_destination(state) == "budget_calculator_node"

    # Revision run (revision_count > 0)
    state["revision_count"] = 1
    assert route_after_destination(state) == "logistics_routing_node"
