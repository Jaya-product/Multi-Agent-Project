"""Unit tests for LangGraph node implementations."""

import pytest
from src.graph.state import create_initial_state
from src.graph.nodes import (
    parse_requirements_node,
    destination_research_node,
    logistics_routing_node,
    budget_calculator_node,
    review_validator_node,
    revision_dispatcher_node,
    synthesize_final_plan_node,
)
from src.models.request import UserTravelRequest
from src.models.itinerary import FinalItineraryPlan


def test_parse_requirements_node():
    state = create_initial_state("Plan a 3-day cultural and beach trip to Dubai with a budget of 4000 AED")
    result = parse_requirements_node(state)
    assert "user_request" in result
    user_req: UserTravelRequest = result["user_request"]
    assert user_req.duration_days == 3
    assert user_req.budget_aed == 4000.0
    assert "culture" in user_req.interests
    assert "beach" in user_req.interests
    assert len(result["node_traces"]) == 1


def test_destination_research_node():
    state = create_initial_state("3 days culture trip")
    state["user_request"] = UserTravelRequest(
        raw_prompt="3 days culture trip",
        duration_days=3,
        budget_aed=5000.0,
        interests=["culture"],
        avoid_crowds=True,
    )
    result = destination_research_node(state)
    assert "candidate_attractions" in result
    assert "candidate_dining" in result
    assert len(result["candidate_attractions"]) > 0
    assert len(result["candidate_dining"]) > 0
    assert any(a.category == "culture" for a in result["candidate_attractions"])


def test_logistics_routing_node():
    state = create_initial_state("2 days trip")
    state["user_request"] = UserTravelRequest(
        raw_prompt="2 days trip",
        duration_days=2,
        budget_aed=4000.0,
        interests=["culture"],
        hotel_tier="budget",
    )
    # Research candidates first
    dest_res = destination_research_node(state)
    state["candidate_attractions"] = dest_res["candidate_attractions"]
    state["candidate_dining"] = dest_res["candidate_dining"]

    result = logistics_routing_node(state)
    assert "selected_hotel_zone" in result
    assert "daily_schedules" in result
    assert len(result["daily_schedules"]) == 2
    for day in result["daily_schedules"]:
        assert day.morning_activity is not None
        assert day.lunch_spot is not None
        assert day.afternoon_activity is not None
        assert day.evening_activity is not None
        assert len(day.transit_connections) >= 3


def test_budget_calculator_node():
    state = create_initial_state("2 days budget trip")
    state["user_request"] = UserTravelRequest(
        raw_prompt="2 days budget trip",
        duration_days=2,
        budget_aed=5000.0,
        interests=["culture"],
    )
    dest_res = destination_research_node(state)
    state["candidate_attractions"] = dest_res["candidate_attractions"]
    state["candidate_dining"] = dest_res["candidate_dining"]
    log_res = logistics_routing_node(state)
    state["selected_hotel_zone"] = log_res["selected_hotel_zone"]
    state["daily_schedules"] = log_res["daily_schedules"]

    result = budget_calculator_node(state)
    assert "budget_summary" in result
    assert result["budget_summary"].total_cost > 0.0
    assert result["budget_summary"].accommodation_cost > 0.0
    assert result["budget_summary"].activities_cost >= 0.0


def test_review_and_dispatcher_nodes():
    state = create_initial_state("2 days trip")
    state["user_request"] = UserTravelRequest(
        raw_prompt="2 days trip",
        duration_days=2,
        budget_aed=5000.0,
        interests=["culture"],
    )
    dest_res = destination_research_node(state)
    state["candidate_attractions"] = dest_res["candidate_attractions"]
    state["candidate_dining"] = dest_res["candidate_dining"]
    log_res = logistics_routing_node(state)
    state["selected_hotel_zone"] = log_res["selected_hotel_zone"]
    state["daily_schedules"] = log_res["daily_schedules"]
    bud_res = budget_calculator_node(state)
    state["budget_summary"] = bud_res["budget_summary"]

    review_res = review_validator_node(state)
    assert "review_result" in review_res
    state["review_result"] = review_res["review_result"]

    # Test dispatcher
    disp_res = revision_dispatcher_node(state)
    assert "revision_count" in disp_res
    assert disp_res["revision_count"] == 1
    assert "revision_instructions" in disp_res


def test_synthesize_final_plan_node():
    state = create_initial_state("3 days trip")
    state["user_request"] = UserTravelRequest(
        raw_prompt="3 days trip",
        duration_days=3,
        budget_aed=5000.0,
        interests=["culture", "beach"],
    )
    dest_res = destination_research_node(state)
    state["candidate_attractions"] = dest_res["candidate_attractions"]
    state["candidate_dining"] = dest_res["candidate_dining"]
    log_res = logistics_routing_node(state)
    state["selected_hotel_zone"] = log_res["selected_hotel_zone"]
    state["daily_schedules"] = log_res["daily_schedules"]
    bud_res = budget_calculator_node(state)
    state["budget_summary"] = bud_res["budget_summary"]
    review_res = review_validator_node(state)
    state["review_result"] = review_res["review_result"]

    synth_res = synthesize_final_plan_node(state)
    assert "final_plan" in synth_res
    plan: FinalItineraryPlan = synth_res["final_plan"]
    assert plan.user_profile.duration_days == 3
    assert len(plan.days) == 3
    assert plan.budget_breakdown is not None
    assert plan.review_summary is not None
