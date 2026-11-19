"""User travel request schema."""

from typing import List, Literal
from pydantic import BaseModel, Field


class UserTravelRequest(BaseModel):
    """Normalized travel requirements extracted from user prompt."""

    raw_prompt: str
    duration_days: int = Field(default=4, ge=1, le=7, description="Trip duration in days (1 to 7)")
    budget_aed: float = Field(default=5000.0, gt=0, description="Total budget in AED")
    interests: List[str] = Field(
        default_factory=list,
        description="List of traveler interests: e.g., culture, beach, dining, shopping, sightseeing"
    )
    hotel_tier: Literal["budget", "midscale", "luxury"] = Field(
        default="budget",
        description="Target accommodation tier"
    )
    pace: Literal["relaxed", "moderate", "fast-paced"] = Field(
        default="moderate",
        description="Pacing of daily itinerary"
    )
    avoid_crowds: bool = Field(
        default=True,
        description="Whether to prioritize low/medium crowd attractions"
    )
