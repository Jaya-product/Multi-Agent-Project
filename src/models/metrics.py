"""Telemetry, profiling, and evaluation metrics models."""

from typing import List
from pydantic import BaseModel, Field


class NodeExecutionMetric(BaseModel):
    """Execution performance for an individual LangGraph node."""

    node_name: str
    latency_seconds: float = Field(ge=0.0)
    tokens_input: int = Field(default=0, ge=0)
    tokens_output: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)


class GraphExecutionMetrics(BaseModel):
    """Aggregate observability metrics across entire run."""

    thread_id: str
    total_latency_seconds: float = Field(ge=0.0)
    node_metrics: List[NodeExecutionMetric] = Field(default_factory=list)
    revision_count: int = Field(default=0, ge=0)
    budget_compliant: bool = True
    preference_score: float = Field(default=1.0, ge=0.0, le=1.0)
    coherence_score: float = Field(default=1.0, ge=0.0, le=1.0)
