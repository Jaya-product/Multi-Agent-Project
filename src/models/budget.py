"""Budget calculations and alternative option models."""

from typing import TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.models.itinerary import ActivityItem


class BudgetSummary(BaseModel):
    """Aggregated expenses and compliance indicators."""

    accommodation_cost: float = Field(ge=0.0)
    activities_cost: float = Field(ge=0.0)
    dining_cost: float = Field(ge=0.0)
    transport_cost: float = Field(ge=0.0)
    total_cost: float = Field(ge=0.0)
    budget_limit: float = Field(gt=0.0)
    is_compliant: bool
    variance_aed: float = 0.0  # Positive = under budget, Negative = over budget


class AlternativeOption(BaseModel):
    """Lower-cost alternative to resolve budget or constraint overages."""

    original_item_name: str
    replacement_item: "ActivityItem"
    savings_aed: float = Field(ge=0.0)
    rationale: str
