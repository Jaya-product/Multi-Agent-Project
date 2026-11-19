"""Deterministic Python validation and constraint enforcement engine."""

from typing import List, Dict, Any, Optional
from configs.dubai_constants import (
    DEFAULT_CONTINGENCY_BUFFER,
    MAX_DAILY_ACTIVE_HOURS,
    MAX_TRANSIT_LEG_MINUTES,
)
from src.models.review import ReviewResult
from src.models.itinerary import DailyPlan
from src.models.budget import BudgetSummary
from src.models.request import UserTravelRequest


def verify_constraints_rule_engine(
    days: List[DailyPlan],
    budget_summary: BudgetSummary,
    user_request: UserTravelRequest,
    contingency_buffer: float = DEFAULT_CONTINGENCY_BUFFER,
) -> ReviewResult:
    """Execute deterministic 5-rule check against drafted itinerary and financial summary.
    
    Returns:
        ReviewResult with approved=True if zero violations, or approved=False with explicit violations list.
    """
    violations: List[str] = []

    # -------------------------------------------------------------
    # Rule 1: Total Budget Cap Check (with 10% contingency buffer)
    # -------------------------------------------------------------
    total_with_buffer = round(budget_summary.total_cost * (1.0 + contingency_buffer), 2)
    budget_limit = user_request.budget_aed

    if total_with_buffer > budget_limit:
        overage = round(total_with_buffer - budget_limit, 2)
        violations.append(
            f"OVER_BUDGET: Total spend AED {total_with_buffer:.2f} (including 10% buffer) "
            f"exceeds user budget limit AED {budget_limit:.2f} by AED {overage:.2f}"
        )

    # -------------------------------------------------------------
    # Rule 2: Daily Pacing Check (Active hours <= 8.5h per day)
    # -------------------------------------------------------------
    for day in days:
        active_hours = sum([
            day.morning_activity.duration_hours if day.morning_activity else 0.0,
            day.lunch_spot.duration_hours if day.lunch_spot else 0.0,
            day.afternoon_activity.duration_hours if day.afternoon_activity else 0.0,
            day.evening_activity.duration_hours if day.evening_activity else 0.0,
        ])
        if active_hours > MAX_DAILY_ACTIVE_HOURS:
            violations.append(
                f"PACE_EXCEEDED: Day {day.day_number} scheduled active time ({active_hours:.1f}h) "
                f"exceeds maximum allowed ceiling of {MAX_DAILY_ACTIVE_HOURS}h"
            )

    # -------------------------------------------------------------
    # Rule 3: Spatial Transit Feasibility Check (Transit <= 45 min)
    # -------------------------------------------------------------
    for day in days:
        for seg in day.transit_connections:
            if seg.duration_minutes > MAX_TRANSIT_LEG_MINUTES:
                violations.append(
                    f"EXCESSIVE_TRANSIT: Day {day.day_number} transit from '{seg.origin}' to "
                    f"'{seg.destination}' takes {seg.duration_minutes} min (exceeds {int(MAX_TRANSIT_LEG_MINUTES)} min threshold)"
                )

    # -------------------------------------------------------------
    # Rule 4: Mandatory Preference Adherence
    # -------------------------------------------------------------
    all_activities = []
    for day in days:
        for act in [day.morning_activity, day.lunch_spot, day.afternoon_activity, day.evening_activity]:
            if act:
                all_activities.append(act)

    present_categories = {a.category.lower() for a in all_activities}

    for interest in user_request.interests:
        norm_int = interest.strip().lower()
        if norm_int in ["culture", "heritage", "history"] and "culture" not in present_categories:
            violations.append("PREFERENCE_OMISSION: Cultural/heritage activities requested but omitted in schedule")
        elif norm_int in ["beach", "beaches", "coastal"] and "beach" not in present_categories:
            violations.append("PREFERENCE_OMISSION: Beach/coastal relaxation requested but omitted in schedule")
        elif norm_int in ["shopping", "souks", "malls"] and "shopping" not in present_categories:
            violations.append("PREFERENCE_OMISSION: Shopping/souks requested but omitted in schedule")
        elif norm_int in ["adventure", "theme park"] and "adventure" not in present_categories:
            violations.append("PREFERENCE_OMISSION: Adventure/theme park activities requested but omitted in schedule")

    # -------------------------------------------------------------
    # Rule 5: Deduplication Check (Zero duplicate venues across trip)
    # -------------------------------------------------------------
    seen_names = set()
    for act in all_activities:
        name_lower = act.name.strip().lower()
        if name_lower in seen_names:
            violations.append(f"DUPLICATE_ACTIVITY: Venue '{act.name}' is scheduled more than once across the itinerary")
        seen_names.add(name_lower)

    # Formulate verdict and corrective guidance
    approved = (len(violations) == 0)
    instructions = None
    if not approved:
        instructions = "; ".join(violations)

    return ReviewResult(
        approved=approved,
        violations=violations,
        revision_instructions=instructions,
        iteration=1,
    )
