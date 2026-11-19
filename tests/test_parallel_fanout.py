"""Tests for Send API dynamic parallel fan-out and annotated state reducers."""

import pytest
from langgraph.types import Send
from src.graph.state import create_initial_state, TravelPlanState
from src.graph.edges import parallel_exploration_router
from src.graph.nodes import destination_research_node, logistics_routing_node
from src.models.request import UserTravelRequest
from src.models.enums import DataSource
from src.models.itinerary import ActivityItem


def test_parallel_exploration_router_returns_sends():
    state = create_initial_state("3-day culture trip to Dubai")
    state["user_request"] = UserTravelRequest(
        raw_prompt="3-day culture trip",
        duration_days=3,
        budget_aed=5000.0,
        interests=["culture"],
    )

    sends = parallel_exploration_router(state)
    assert len(sends) == 2
    assert all(isinstance(s, Send) for s in sends)

    targets = {s.node for s in sends}
    assert "destination_research_node" in targets
    assert "logistics_routing_node" in targets


def test_state_reducer_merges_parallel_candidate_lists():
    # Simulates what LangGraph does when two parallel workers return candidate lists
    state = create_initial_state("Dubai test")

    dest_output = {
        "candidate_attractions": [
            ActivityItem(
                name="Museum A",
                category="culture",
                neighborhood="Bur Dubai",
                lat=25.26,
                lng=55.29,
                duration_hours=2.0,
                cost_aed=15.0,
                cost_source=DataSource.SEED_DATABASE,
                is_indoor=True,
                crowd_level="low",
            )
        ]
    }

    log_output = {
        "candidate_attractions": [
            ActivityItem(
                name="Beach B",
                category="beach",
                neighborhood="Jumeirah",
                lat=25.16,
                lng=55.20,
                duration_hours=2.5,
                cost_aed=0.0,
                cost_source=DataSource.SEED_DATABASE,
                is_indoor=False,
                crowd_level="medium",
            )
        ]
    }

    # Simulate reducer operator.add
    merged_attractions = state["candidate_attractions"] + dest_output["candidate_attractions"] + log_output["candidate_attractions"]
    assert len(merged_attractions) == 2
    names = [a.name for a in merged_attractions]
    assert "Museum A" in names
    assert "Beach B" in names
