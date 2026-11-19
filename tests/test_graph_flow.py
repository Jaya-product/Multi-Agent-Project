"""End-to-end integration tests for complete LangGraph execution and HITL pauses."""

import pytest
import uuid
from src.graph.builder import build_travel_planner_graph
from src.graph.state import create_initial_state
from src.models.itinerary import FinalItineraryPlan


def test_complete_graph_execution_flow():
    """Verify end-to-end graph execution without human-in-the-loop interruption."""
    graph = build_travel_planner_graph(enable_hitl=False)
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_input = create_initial_state("Plan a 3-day cultural and beach trip to Dubai with a budget of 5000 AED")
    output_state = graph.invoke(initial_input, config=thread_config)

    # 1. State integrity checks
    assert "user_request" in output_state
    user_req = output_state["user_request"]
    assert user_req.duration_days == 3
    assert user_req.budget_aed == 5000.0
    assert "culture" in user_req.interests
    assert "beach" in user_req.interests

    # 2. Daily schedules generated
    daily_schedules = output_state["daily_schedules"]
    assert len(daily_schedules) == 3
    for day in daily_schedules:
        assert day.morning_activity is not None
        assert day.lunch_spot is not None
        assert day.afternoon_activity is not None
        assert day.evening_activity is not None
        assert len(day.transit_connections) >= 3

    # 3. Final synthesized plan
    assert "final_plan" in output_state
    final_plan: FinalItineraryPlan = output_state["final_plan"]
    assert final_plan is not None
    assert final_plan.user_profile.duration_days == 3
    assert len(final_plan.days) == 3
    assert final_plan.budget_breakdown is not None
    assert final_plan.review_summary is not None
    assert final_plan.execution_time_seconds > 0.0

    # 4. Tracing telemetry
    traces = output_state.get("node_traces", [])
    assert len(traces) >= 5
    executed_nodes = {t["node_name"] for t in traces}
    assert "parse_requirements_node" in executed_nodes
    assert "synthesize_final_plan_node" in executed_nodes


def test_human_in_the_loop_pause_and_resume():
    """Verify graph execution pauses at interrupt_before gate and resumes successfully."""
    graph = build_travel_planner_graph(enable_hitl=True)
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    initial_input = create_initial_state("2 days budget sightseeing trip to Dubai with budget 3000 AED")

    # Step 1: Run graph until pause gate
    graph.invoke(initial_input, config=thread_config)

    # Inspect paused state snapshot
    snapshot = graph.get_state(thread_config)
    assert snapshot.next == ("review_validator_node",)
    assert "daily_schedules" in snapshot.values
    assert len(snapshot.values["daily_schedules"]) == 2

    # Step 2: Resume execution from paused gate
    resumed_output = graph.invoke(None, config=thread_config)
    assert "final_plan" in resumed_output
    assert resumed_output["final_plan"] is not None
    assert resumed_output["final_plan"].user_profile.duration_days == 2
