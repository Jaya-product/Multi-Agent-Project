"""Unit tests for deterministic validation rule engine."""

import pytest
from src.tools.validation_engine import verify_constraints_rule_engine
from src.models.request import UserTravelRequest
from src.models.budget import BudgetSummary
from src.models.itinerary import DailyPlan, ActivityItem, TransitSegment
from src.models.enums import DataSource


def make_dummy_activity(name: str, category: str, hours: float = 2.0, cost: float = 50.0) -> ActivityItem:
    return ActivityItem(
        name=name,
        category=category,
        neighborhood="Bur Dubai",
        lat=25.2635,
        lng=55.2972,
        duration_hours=hours,
        cost_aed=cost,
        cost_source=DataSource.SEED_DATABASE,
        is_indoor=False,
        crowd_level="low",
    )


def make_valid_day(day_num: int = 1) -> DailyPlan:
    return DailyPlan(
        day_number=day_num,
        focus_area="Old Dubai",
        morning_activity=make_dummy_activity(f"Museum Day {day_num}", "culture", 2.0, 15.0),
        lunch_spot=make_dummy_activity(f"Lunch Spot Day {day_num}", "dining", 1.5, 40.0),
        afternoon_activity=make_dummy_activity(f"Beach Day {day_num}", "beach", 2.0, 0.0),
        evening_activity=make_dummy_activity(f"Dinner Day {day_num}", "dining", 1.5, 50.0),
        transit_connections=[
            TransitSegment(
                origin="Point A",
                destination="Point B",
                mode="metro",
                duration_minutes=20,
                fare_aed=5.0,
            )
        ],
        day_cost_aed=110.0,
    )


def test_rule_engine_passes_valid_itinerary():
    user = UserTravelRequest(
        raw_prompt="4 days in Dubai, culture and beaches",
        duration_days=2,
        budget_aed=4000.0,
        interests=["culture", "beach"],
    )
    days = [make_valid_day(1), make_valid_day(2)]
    budget = BudgetSummary(
        accommodation_cost=600.0,
        activities_cost=30.0,
        dining_cost=180.0,
        transport_cost=20.0,
        total_cost=830.0,
        budget_limit=4000.0,
        is_compliant=True,
    )

    result = verify_constraints_rule_engine(days, budget, user)
    assert result.approved is True
    assert len(result.violations) == 0


def test_rule_1_detects_over_budget():
    user = UserTravelRequest(
        raw_prompt="Budget trip",
        budget_aed=1000.0,
        interests=["culture"],
    )
    days = [make_valid_day(1)]
    # Total 1000 with 10% buffer = 1100 > 1000
    budget = BudgetSummary(
        accommodation_cost=500.0,
        activities_cost=200.0,
        dining_cost=200.0,
        transport_cost=100.0,
        total_cost=1000.0,
        budget_limit=1000.0,
        is_compliant=False,
    )

    result = verify_constraints_rule_engine(days, budget, user)
    assert result.approved is False
    assert any("OVER_BUDGET" in v for v in result.violations)


def test_rule_2_detects_pace_exceeded():
    user = UserTravelRequest(
        raw_prompt="Relaxed trip",
        budget_aed=5000.0,
        interests=["culture", "beach"],
    )
    # Day with active hours: 3.5 + 2.0 + 3.0 + 1.5 = 10.0h (> 8.5h ceiling)
    overpacked_day = DailyPlan(
        day_number=1,
        focus_area="Downtown",
        morning_activity=make_dummy_activity("Mega Tour", "culture", 3.5),
        lunch_spot=make_dummy_activity("Long Feast", "dining", 2.0),
        afternoon_activity=make_dummy_activity("Theme Park", "adventure", 3.0),
        evening_activity=make_dummy_activity("Opera Dinner", "dining", 1.5),
        transit_connections=[],
        day_cost_aed=300.0,
    )
    budget = BudgetSummary(
        accommodation_cost=300.0,
        activities_cost=200.0,
        dining_cost=100.0,
        transport_cost=50.0,
        total_cost=650.0,
        budget_limit=5000.0,
        is_compliant=True,
    )

    result = verify_constraints_rule_engine([overpacked_day], budget, user)
    assert result.approved is False
    assert any("PACE_EXCEEDED" in v for v in result.violations)


def test_rule_3_detects_excessive_transit():
    user = UserTravelRequest(
        raw_prompt="Trip",
        budget_aed=5000.0,
        interests=["culture"],
    )
    day = make_valid_day(1)
    day.transit_connections = [
        TransitSegment(
            origin="Far Out Suburb",
            destination="Palm Island",
            mode="metro",
            duration_minutes=65,  # Exceeds 45 min threshold
            fare_aed=15.0,
        )
    ]
    budget = BudgetSummary(
        accommodation_cost=300.0,
        activities_cost=50.0,
        dining_cost=90.0,
        transport_cost=30.0,
        total_cost=470.0,
        budget_limit=5000.0,
        is_compliant=True,
    )

    result = verify_constraints_rule_engine([day], budget, user)
    assert result.approved is False
    assert any("EXCESSIVE_TRANSIT" in v for v in result.violations)


def test_rule_4_detects_missing_preference():
    user = UserTravelRequest(
        raw_prompt="Trip with beach",
        budget_aed=5000.0,
        interests=["beach"],
    )
    # Day only has culture and dining, no beach
    day = DailyPlan(
        day_number=1,
        focus_area="Bur Dubai",
        morning_activity=make_dummy_activity("Fort", "culture", 2.0),
        lunch_spot=make_dummy_activity("Bistro", "dining", 1.5),
        afternoon_activity=make_dummy_activity("Museum", "culture", 2.0),
        evening_activity=make_dummy_activity("Tea House", "dining", 1.5),
        transit_connections=[],
        day_cost_aed=100.0,
    )
    budget = BudgetSummary(
        accommodation_cost=300.0,
        activities_cost=50.0,
        dining_cost=90.0,
        transport_cost=30.0,
        total_cost=470.0,
        budget_limit=5000.0,
        is_compliant=True,
    )

    result = verify_constraints_rule_engine([day], budget, user)
    assert result.approved is False
    assert any("PREFERENCE_OMISSION" in v for v in result.violations)


def test_rule_5_detects_duplicate_activities():
    user = UserTravelRequest(
        raw_prompt="Trip",
        budget_aed=5000.0,
        interests=["culture"],
    )
    day1 = DailyPlan(
        day_number=1,
        focus_area="Bur Dubai",
        morning_activity=make_dummy_activity("Dubai Museum", "culture", 2.0),
        lunch_spot=make_dummy_activity("Cafe 1", "dining", 1.5),
        afternoon_activity=make_dummy_activity("Souk", "shopping", 2.0),
        evening_activity=make_dummy_activity("Cafe 2", "dining", 1.5),
        transit_connections=[],
        day_cost_aed=100.0,
    )
    day2 = DailyPlan(
        day_number=2,
        focus_area="Bur Dubai",
        morning_activity=make_dummy_activity("Dubai Museum", "culture", 2.0),  # Duplicate
        lunch_spot=make_dummy_activity("Cafe 3", "dining", 1.5),
        afternoon_activity=make_dummy_activity("Walkway", "sightseeing", 2.0),
        evening_activity=make_dummy_activity("Cafe 4", "dining", 1.5),
        transit_connections=[],
        day_cost_aed=100.0,
    )
    budget = BudgetSummary(
        accommodation_cost=600.0,
        activities_cost=100.0,
        dining_cost=180.0,
        transport_cost=60.0,
        total_cost=940.0,
        budget_limit=5000.0,
        is_compliant=True,
    )

    result = verify_constraints_rule_engine([day1, day2], budget, user)
    assert result.approved is False
    assert any("DUPLICATE_ACTIVITY" in v for v in result.violations)
