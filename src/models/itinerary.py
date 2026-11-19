"""Itinerary components and daily schedule schemas."""

from typing import List, Literal, Optional, ForwardRef
from pydantic import BaseModel, Field
from src.models.enums import DataSource
from src.models.request import UserTravelRequest


class ActivityItem(BaseModel):
    """An individual activity, POI, or restaurant visit in Dubai."""

    name: str
    category: Literal["culture", "beach", "dining", "sightseeing", "shopping", "adventure"]
    neighborhood: str
    lat: float
    lng: float
    duration_hours: float = Field(ge=0.5, le=8.0)
    cost_aed: float = Field(ge=0.0)
    cost_source: DataSource = DataSource.SEED_DATABASE
    is_indoor: bool
    crowd_level: Literal["low", "medium", "high"] = "medium"


class TransitSegment(BaseModel):
    """A point-to-point transit connection between two activities."""

    origin: str
    destination: str
    mode: Literal["metro", "bus", "taxi", "walking", "abra", "monorail"]
    duration_minutes: int = Field(ge=1)
    fare_aed: float = Field(ge=0.0)
    fare_source: DataSource = DataSource.RTA_OFFICIAL


class DailyPlan(BaseModel):
    """Complete schedule for a single calendar day."""

    day_number: int = Field(ge=1)
    focus_area: str
    morning_activity: ActivityItem
    lunch_spot: ActivityItem
    afternoon_activity: ActivityItem
    evening_activity: ActivityItem
    transit_connections: List[TransitSegment] = Field(default_factory=list)
    day_cost_aed: float = Field(ge=0.0, default=0.0)


# Import forward refs when needed
from src.models.budget import BudgetSummary, AlternativeOption
from src.models.review import ReviewResult


class FinalItineraryPlan(BaseModel):
    """Final validated travel plan presented to the user."""

    trip_title: str
    thread_id: str
    user_profile: UserTravelRequest
    days: List[DailyPlan]
    budget_breakdown: BudgetSummary
    alternatives: List[AlternativeOption] = Field(default_factory=list)
    review_summary: ReviewResult
    execution_time_seconds: float = 0.0
