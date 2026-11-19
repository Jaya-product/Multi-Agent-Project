"""Tests verifying 100% offline resilience and graceful local fallbacks."""

import pytest
from unittest.mock import patch
import requests
import uuid
from src.data_access.osrm_client import OSRMClient
from src.data_access.open_meteo import OpenMeteoClient
from src.data_access.repository import DubaiDataRepository
from src.models.enums import DataSource
from src.graph.builder import build_travel_planner_graph
from src.graph.state import create_initial_state


def test_osrm_offline_fallback():
    """Verify OSRM falls back to local Haversine formula on network failure."""
    client = OSRMClient(timeout_seconds=0.1)

    # Force request to fail
    with patch("requests.get", side_effect=requests.ConnectionError("Simulated network outage")):
        route = client.calculate_road_route(
            origin_lat=25.2048,
            origin_lon=55.2708,
            dest_lat=25.0805,
            dest_lon=55.1403,
        )

    assert route is not None
    assert route["distance_km"] > 0
    assert route["duration_minutes"] >= 6
    assert route["taxi_fare_aed"] >= 12.0
    assert route["source"] == DataSource.RTA_OFFICIAL


def test_open_meteo_offline_fallback():
    """Verify Open-Meteo falls back to local baseline weather on timeout or network error."""
    client = OpenMeteoClient(timeout_seconds=0.1)

    with patch("requests.get", side_effect=requests.Timeout("Simulated timeout")):
        forecast = client.get_forecast(days=3)

    assert forecast is not None
    assert len(forecast["dates"]) == 3
    assert forecast["is_outdoor_friendly"] is True
    assert forecast["source"] == DataSource.SEED_DATABASE


def test_repository_offline_full_operation():
    """Verify DubaiDataRepository methods succeed completely offline."""
    repo = DubaiDataRepository.get_instance()

    with patch("requests.get", side_effect=requests.ConnectionError("Network disconnected")):
        # 1. Attractions & Dining (pure local SQLite)
        pois = repo.search_attractions(category="culture", limit=3)
        assert len(pois) > 0

        dining = repo.search_dining(price_tier="budget", limit=3)
        assert len(dining) > 0

        # 2. Weather
        weather = repo.get_weather_forecast(days=3)
        assert weather["source"] == DataSource.SEED_DATABASE

        # 3. Transit route (local matrix or Haversine fallback)
        transit = repo.calculate_transit_route(
            origin_name="Burj Khalifa",
            dest_name="Dubai Marina",
            origin_lat=25.1972,
            origin_lng=55.2744,
            dest_lat=25.0805,
            dest_lng=55.1403,
            origin_neighborhood="Downtown",
            dest_neighborhood="Dubai Marina",
            preferred_mode="taxi",
        )
        assert transit.duration_minutes > 0
        assert transit.fare_aed > 0


def test_end_to_end_graph_execution_completely_offline():
    """Verify complete LangGraph flow runs without any external HTTP network access."""
    graph = build_travel_planner_graph(enable_hitl=False)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    prompt = "3 days in Dubai with 5000 AED budget, culture and food"
    initial_state = create_initial_state(prompt)

    # Block all external network calls
    with patch("requests.get", side_effect=requests.ConnectionError("Offline mode")):
        output = graph.invoke(initial_state, config=config)

    assert output.get("final_plan") is not None
    plan = output["final_plan"]
    assert len(plan.days) == 3
    assert plan.budget_breakdown is not None
    assert plan.execution_time_seconds > 0.0
