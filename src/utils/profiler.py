"""Performance profiling and telemetry metrics calculation."""

import time
from typing import List, Dict, Any, Optional
from src.models.metrics import NodeExecutionMetric, GraphExecutionMetrics


class ExecutionProfiler:
    """Tracks latency, token usage, and costs per LangGraph node invocation."""

    def __init__(self):
        self._node_metrics: List[NodeExecutionMetric] = []
        self._start_time: float = time.perf_counter()

    def record_node_execution(
        self,
        node_name: str,
        latency_seconds: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_per_million_input: float = 0.15,   # Gemini 2.5 Flash baseline pricing
        cost_per_million_output: float = 0.60,
    ) -> NodeExecutionMetric:
        """Calculate cost estimate and record metric for a completed node."""
        cost = (
            (tokens_input / 1_000_000.0) * cost_per_million_input
            + (tokens_output / 1_000_000.0) * cost_per_million_output
        )
        metric = NodeExecutionMetric(
            node_name=node_name,
            latency_seconds=round(latency_seconds, 3),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            estimated_cost_usd=round(cost, 6),
        )
        self._node_metrics.append(metric)
        return metric

    def compile_graph_metrics(
        self,
        thread_id: str,
        revision_count: int = 0,
        budget_compliant: bool = True,
    ) -> GraphExecutionMetrics:
        """Compile aggregate execution metrics for the full workflow."""
        total_latency = round(time.perf_counter() - self._start_time, 3)
        return GraphExecutionMetrics(
            thread_id=thread_id,
            total_latency_seconds=total_latency,
            node_metrics=list(self._node_metrics),
            revision_count=revision_count,
            budget_compliant=budget_compliant,
            preference_score=1.0,
            coherence_score=1.0,
        )
