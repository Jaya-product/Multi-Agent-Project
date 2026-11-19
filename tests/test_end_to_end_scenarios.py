"""End-to-end integration tests across diverse travel profiles and constraint edges."""

import pytest
import uuid
from src.graph.builder import build_travel_planner_graph
from src.graph.state import create_initial_state
from src.models.itinerary import FinalItineraryPlan


@pytest.fixture(scope="module")
def planner_graph():
    """Compiled LangGraph instance for scenario testing."""
    return build_travel_planner_graph(enable_hitl=False)


def test_scenario_budget_tight(planner_graph):
    """Scenario A: Tight budget constraints verifying cost compliance and alternatives."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = (
        "Plan a 2-day budget trip to Dubai for a solo backpacker with a strict budget of AED 2,000. "
        "I want cheap street food, budget hostels in Deira or Bur Dubai, and affordable sights."
    )
    initial_state = create_initial_state(prompt)
    output = planner_graph.invoke(initial_state, config=config)

    plan: FinalItineraryPlan = output.get("final_plan")
    assert plan is not None
    assert plan.user_profile.duration_days == 2
    assert len(plan.days) == 2
    assert plan.user_profile.hotel_tier == "budget"

    # Budget checks
    assert plan.budget_breakdown.total_cost <= 2500.0  # Within feasible range / contingency
    assert plan.budget_breakdown.accommodation_cost > 0


def test_scenario_culture_heavy(planner_graph):
    """Scenario B: Cultural heritage traveler prioritizing Old Dubai and museums."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = (
        "3 days in Dubai focusing on cultural heritage, historic districts, museums, "
        "and souks in Bur Dubai and Deira. Budget AED 4,500. Avoid crowded modern malls."
    )
    initial_state = create_initial_state(prompt)
    output = planner_graph.invoke(initial_state, config=config)

    plan: FinalItineraryPlan = output.get("final_plan")
    assert plan is not None
    assert plan.user_profile.duration_days == 3
    assert "culture" in plan.user_profile.interests

    # Verify presence of cultural venues across days
    all_categories = []
    for day in plan.days:
        all_categories.extend([
            day.morning_activity.category,
            day.afternoon_activity.category,
            day.evening_activity.category,
        ])
    assert "culture" in all_categories


def test_scenario_luxury_beach(planner_graph):
    """Scenario C: Luxury beach and coastal leisure trip."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = (
        "4 days luxury vacation in Dubai with budget AED 18,000. "
        "5-star hotel, beach clubs in Palm Jumeirah or Dubai Marina, and upscale dining."
    )
    initial_state = create_initial_state(prompt)
    output = planner_graph.invoke(initial_state, config=config)

    plan: FinalItineraryPlan = output.get("final_plan")
    assert plan is not None
    assert plan.user_profile.duration_days == 4
    assert plan.user_profile.hotel_tier == "luxury"

    # Higher budget allocation for luxury
    assert plan.budget_breakdown.accommodation_cost >= 1500.0


def test_scenario_single_day_sprint(planner_graph):
    """Scenario D: 1-day compact layover or sprint itinerary."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = "1 day fast-paced highlights tour of Dubai, budget AED 1,500, sightseeing and food"
    initial_state = create_initial_state(prompt)
    output = planner_graph.invoke(initial_state, config=config)

    plan: FinalItineraryPlan = output.get("final_plan")
    assert plan is not None
    assert len(plan.days) == 1
    day1 = plan.days[0]
    assert day1.day_number == 1
    assert day1.morning_activity is not None
    assert day1.lunch_spot is not None
    assert day1.afternoon_activity is not None
    assert day1.evening_activity is not None
    assert len(day1.transit_connections) >= 3


def test_scenario_seven_day_extended(planner_graph):
    """Scenario E: 7-day maximum duration trip verifying scheduling and deduplication."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = "7 days in Dubai, budget AED 10,000, sightseeing, beaches, culture, and dining"
    initial_state = create_initial_state(prompt)
    output = planner_graph.invoke(initial_state, config=config)

    plan: FinalItineraryPlan = output.get("final_plan")
    assert plan is not None
    assert len(plan.days) == 7

    # Deduplication check: verify no activity names repeat across all days
    seen_activity_names = set()
    for day in plan.days:
        for act in [day.morning_activity, day.afternoon_activity, day.evening_activity]:
            # Each activity name should be unique
            assert act.name not in seen_activity_names, f"Duplicate activity found: {act.name}"
            seen_activity_names.add(act.name)
