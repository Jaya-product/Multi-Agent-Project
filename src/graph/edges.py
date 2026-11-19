"""Routing functions, Send API parallel fan-out, and conditional edges."""

from typing import List, Literal
from langgraph.types import Send
from src.graph.state import TravelPlanState
from configs.dubai_constants import MAX_REVIEW_ITERATIONS


def parallel_exploration_router(state: TravelPlanState) -> List[Send]:
    """Fan out Destination Research and Logistics concurrently using Send API.
    
    Both branches execute in parallel worker threads and write to annotated
    list reducers in TravelPlanState without race conditions.
    """
    return [
        Send("destination_research_node", state),
        Send("logistics_routing_node", state),
    ]


def route_after_destination(state: TravelPlanState) -> Literal["budget_calculator_node", "logistics_routing_node"]:
    """Route after destination research.
    
    During the initial fan-out (revision_count == 0), joins with logistics into budget.
    During self-correction (revision_count > 0), routes to logistics node to integrate
    new candidates into daily schedules before budget recalculation.
    """
    if state.get("revision_count", 0) > 0:
        return "logistics_routing_node"
    return "budget_calculator_node"


def route_review_verdict(
    state: TravelPlanState,
) -> Literal["synthesize_final_plan_node", "revision_dispatcher_node"]:
    """Evaluate review verdict with a hard iteration guard (default 3 retries).
    
    - If review passed (approved=True): route to synthesis.
    - If review failed but reached max iterations: force completion with partial warning.
    - If review failed and iterations remain: route to revision dispatcher.
    """
    review = state.get("review_result")

    # Pass condition
    if review and review.approved:
        return "synthesize_final_plan_node"

    # Safety Guard: Hard ceiling to prevent infinite recursion
    rev_count = state.get("revision_count", 0)
    if rev_count >= MAX_REVIEW_ITERATIONS:
        # Append warning to error log
        if "error_log" not in state or state["error_log"] is None:
            state["error_log"] = []
        state["error_log"].append(
            f"Review iterations reached hard ceiling ({MAX_REVIEW_ITERATIONS}). "
            "Forcing plan completion with [PARTIAL_VALIDATION] badge."
        )
        return "synthesize_final_plan_node"

    # Fail condition -> route to dispatcher for re-work
    return "revision_dispatcher_node"


def route_revision_target(
    state: TravelPlanState,
) -> Literal["budget_calculator_node", "logistics_routing_node", "destination_research_node"]:
    """Direct re-work to the specific node responsible for the primary violation."""
    review = state.get("review_result")
    violations = review.violations if review else []

    # Priority 1: Financial violations -> Budget Node
    for v in violations:
        if "OVER_BUDGET" in v:
            return "budget_calculator_node"

    # Priority 2: Pacing or transit issues -> Logistics Node
    for v in violations:
        if "PACE_EXCEEDED" in v or "EXCESSIVE_TRANSIT" in v:
            return "logistics_routing_node"

    # Priority 3: Preference omission or duplicate venue -> Destination Node
    for v in violations:
        if "PREFERENCE_OMISSION" in v or "DUPLICATE_ACTIVITY" in v:
            return "destination_research_node"

    return "destination_research_node"
