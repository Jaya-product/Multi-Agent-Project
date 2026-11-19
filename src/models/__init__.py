"""Domain models package with consolidated exports."""

from src.models.enums import DataSource
from src.models.request import UserTravelRequest
from src.models.review import ReviewResult
from src.models.itinerary import (
    ActivityItem,
    TransitSegment,
    DailyPlan,
    FinalItineraryPlan,
)
from src.models.budget import (
    BudgetSummary,
    AlternativeOption,
)
from src.models.metrics import (
    NodeExecutionMetric,
    GraphExecutionMetrics,
)

# Rebuild models that use forward references
AlternativeOption.model_rebuild()
FinalItineraryPlan.model_rebuild()

__all__ = [
    "DataSource",
    "UserTravelRequest",
    "ActivityItem",
    "TransitSegment",
    "DailyPlan",
    "FinalItineraryPlan",
    "BudgetSummary",
    "AlternativeOption",
    "ReviewResult",
    "NodeExecutionMetric",
    "GraphExecutionMetrics",
]
