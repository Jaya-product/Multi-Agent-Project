"""Unit tests for Phase 4 Streamlit UI components and data visualizations."""

import pytest
from src.models.enums import DataSource
from src.models.request import UserTravelRequest
from src.models.itinerary import ActivityItem, TransitSegment, DailyPlan, FinalItineraryPlan
from src.models.budget import BudgetSummary, AlternativeOption
from src.models.review import ReviewResult
from app.components.itinerary_view import get_provenance_badge_html, generate_markdown_summary
from app.components.budget_charts import render_budget_breakdown_chart, render_daily_spend_bar_chart
from app.components.trace_viewer import render_progress_stepper


@pytest.fixture
def sample_plan() -> FinalItineraryPlan:
    """Fixture providing a mock FinalItineraryPlan for UI testing."""
    user = UserTravelRequest(
        raw_prompt="3 days in Dubai, culture and dining, budget 4000 AED",
        duration_days=2,
        budget_aed=4000.0,
        interests=["culture", "dining"],
        hotel_tier="budget",
        pace="moderate",
        avoid_crowds=True,
    )

    act1 = ActivityItem(
        name="Dubai Museum",
        category="culture",
        neighborhood="Bur Dubai",
        lat=25.263,
        lng=55.297,
        duration_hours=2.0,
        cost_aed=15.0,
        cost_source=DataSource.SEED_DATABASE,
        is_indoor=True,
        crowd_level="low",
    )
    dine1 = ActivityItem(
        name="Al Ustad Special Kabab",
        category="dining",
        neighborhood="Bur Dubai",
        lat=25.260,
        lng=55.299,
        duration_hours=1.5,
        cost_aed=60.0,
        cost_source=DataSource.SEED_DATABASE,
        is_indoor=True,
        crowd_level="medium",
    )
    act2 = ActivityItem(
        name="Al Fahidi Historical Neighbourhood",
        category="culture",
        neighborhood="Bur Dubai",
        lat=25.264,
        lng=55.300,
        duration_hours=2.5,
        cost_aed=0.0,
        cost_source=DataSource.SEED_DATABASE,
        is_indoor=False,
        crowd_level="low",
    )
    act3 = ActivityItem(
        name="Dubai Frame",
        category="sightseeing",
        neighborhood="Zabeel",
        lat=25.234,
        lng=55.300,
        duration_hours=2.0,
        cost_aed=52.5,
        cost_source=DataSource.SEED_DATABASE,
        is_indoor=True,
        crowd_level="medium",
    )

    trans1 = TransitSegment(
        origin="Dubai Museum",
        destination="Al Ustad Special Kabab",
        mode="walking",
        duration_minutes=8,
        fare_aed=0.0,
        fare_source=DataSource.RTA_OFFICIAL,
    )

    day1 = DailyPlan(
        day_number=1,
        focus_area="Bur Dubai",
        morning_activity=act1,
        lunch_spot=dine1,
        afternoon_activity=act2,
        evening_activity=act3,
        transit_connections=[trans1],
        day_cost_aed=127.5,
    )

    budget = BudgetSummary(
        accommodation_cost=800.0,
        activities_cost=135.0,
        dining_cost=180.0,
        transport_cost=45.0,
        total_cost=1160.0,
        budget_limit=4000.0,
        is_compliant=True,
        variance_aed=2840.0,
    )

    review = ReviewResult(
        approved=True,
        violations=[],
        iteration=1,
    )

    return FinalItineraryPlan(
        trip_title="2-Day Dubai Cultural Heritage Tour",
        thread_id="test-thread-1234",
        user_profile=user,
        days=[day1],
        budget_breakdown=budget,
        alternatives=[],
        review_summary=review,
        execution_time_seconds=1.25,
    )


def test_provenance_badge_html():
    """Verify that all DataSource enums generate valid HTML badges."""
    for source in DataSource:
        html = get_provenance_badge_html(source)
        assert "<span class=\"badge-provenance" in html
        assert "</span>" in html


def test_budget_donut_chart_generation(sample_plan):
    """Verify that Plotly donut chart generates without errors and has correct total."""
    fig = render_budget_breakdown_chart(sample_plan.budget_breakdown)
    assert fig is not None
    assert len(fig.data) == 1
    assert fig.data[0].type == "pie"
    assert sum(fig.data[0].values) == sample_plan.budget_breakdown.total_cost


def test_daily_spend_bar_chart(sample_plan):
    """Verify that Plotly stacked bar chart compiles with daily activities and dining."""
    fig = render_daily_spend_bar_chart(sample_plan.days)
    assert fig is not None
    assert len(fig.data) == 3  # Activities, Dining, Transit
    assert fig.data[0].name == "Activities"


def test_markdown_summary_generation(sample_plan):
    """Verify that the markdown export generator creates detailed text."""
    md = generate_markdown_summary(sample_plan)
    assert "# 2-Day Dubai Cultural Heritage Tour" in md
    assert "Bur Dubai" in md
    assert "Dubai Museum" in md
    assert "AED 1,160.0" in md
