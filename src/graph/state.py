"""Centralized TypedDict state for LangGraph multi-agent execution."""

import operator
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from src.models.request import UserTravelRequest
from src.models.itinerary import ActivityItem, DailyPlan, FinalItineraryPlan
from src.models.budget import BudgetSummary, AlternativeOption
from src.models.review import ReviewResult


class TravelPlanState(TypedDict, total=False):
    """Centralized shared state passed across all LangGraph nodes."""

    # User Input & Parsed Constraints
    raw_prompt: str
    user_request: Optional[UserTravelRequest]

    # Domain Working Memory (Annotated with operator.add for safe parallel fan-out)
    candidate_attractions: Annotated[List[ActivityItem], operator.add]
    candidate_dining: Annotated[List[ActivityItem], operator.add]
    selected_hotel_zone: Dict[str, Any]
    daily_schedules: List[DailyPlan]

    # Financial Working Memory
    budget_summary: Optional[BudgetSummary]
    alternative_options: List[AlternativeOption]

    # QA & Self-Correction Loop Control
    review_result: Optional[ReviewResult]
    revision_count: int
    revision_instructions: Optional[str]
    error_log: Annotated[List[str], operator.add]
    node_traces: Annotated[List[Dict[str, Any]], operator.add]

    # Final Structured Deliverable
    final_plan: Optional[FinalItineraryPlan]


def create_initial_state(raw_prompt: str) -> TravelPlanState:
    """Helper to initialize fresh state dictionary for a new travel request."""
    return {
        "raw_prompt": raw_prompt,
        "user_request": None,
        "candidate_attractions": [],
        "candidate_dining": [],
        "selected_hotel_zone": {},
        "daily_schedules": [],
        "budget_summary": None,
        "alternative_options": [],
        "review_result": None,
        "revision_count": 0,
        "revision_instructions": None,
        "error_log": [],
        "node_traces": [],
        "final_plan": None,
    }
