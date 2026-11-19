"""Assembly, conditional wiring, and compilation of the StateGraph engine."""

from typing import Optional, Any
from langgraph.graph import StateGraph, START, END
from configs.settings import get_settings
from src.graph.state import TravelPlanState
from src.graph.checkpointer import get_checkpointer
from src.graph.nodes import (
    parse_requirements_node,
    destination_research_node,
    logistics_routing_node,
    budget_calculator_node,
    review_validator_node,
    revision_dispatcher_node,
    synthesize_final_plan_node,
)
from src.graph.edges import (
    parallel_exploration_router,
    route_after_destination,
    route_review_verdict,
    route_revision_target,
)


def build_travel_planner_graph(
    enable_hitl: Optional[bool] = None,
    checkpointer: Optional[Any] = None,
) -> Any:
    """Construct and compile the multi-agent travel planning StateGraph.
    
    Args:
        enable_hitl: If True, adds interrupt_before=["review_validator_node"] for human review.
                     If None, defaults to AppSettings.enable_human_in_the_loop.
        checkpointer: Checkpointer instance (defaults to MemorySaver).
        
    Returns:
        CompiledStateGraph ready for execution.
    """
    settings = get_settings()
    hitl_flag = enable_hitl if enable_hitl is not None else settings.enable_human_in_the_loop

    # 1. Initialize StateGraph with typed schema
    builder = StateGraph(TravelPlanState)

    # 2. Add Specialized Agent Nodes
    builder.add_node("parse_requirements_node", parse_requirements_node)
    builder.add_node("destination_research_node", destination_research_node)
    builder.add_node("logistics_routing_node", logistics_routing_node)
    builder.add_node("budget_calculator_node", budget_calculator_node)
    builder.add_node("review_validator_node", review_validator_node)
    builder.add_node("revision_dispatcher_node", revision_dispatcher_node)
    builder.add_node("synthesize_final_plan_node", synthesize_final_plan_node)

    # 3. Add Edges & Flow Control
    # Entry edge
    builder.add_edge(START, "parse_requirements_node")

    # Parallel fan-out via Send API
    builder.add_conditional_edges(
        "parse_requirements_node",
        parallel_exploration_router,
    )

    # Destination node: joins into Budget on initial run, or Logistics on revision
    builder.add_conditional_edges(
        "destination_research_node",
        route_after_destination,
        {
            "budget_calculator_node": "budget_calculator_node",
            "logistics_routing_node": "logistics_routing_node",
        },
    )

    # Logistics joins into Budget node
    builder.add_edge("logistics_routing_node", "budget_calculator_node")

    # Budget node flows to Review Validator
    builder.add_edge("budget_calculator_node", "review_validator_node")

    # Review node: Pass -> Synthesis, Fail -> Dispatcher
    builder.add_conditional_edges(
        "review_validator_node",
        route_review_verdict,
        {
            "synthesize_final_plan_node": "synthesize_final_plan_node",
            "revision_dispatcher_node": "revision_dispatcher_node",
        },
    )

    # Dispatcher node: Targeted re-routing based on violation type
    builder.add_conditional_edges(
        "revision_dispatcher_node",
        route_revision_target,
        {
            "budget_calculator_node": "budget_calculator_node",
            "logistics_routing_node": "logistics_routing_node",
            "destination_research_node": "destination_research_node",
        },
    )

    # Terminal edge
    builder.add_edge("synthesize_final_plan_node", END)

    # 4. Checkpointer & Human-in-the-Loop Interrupts
    active_checkpointer = checkpointer if checkpointer is not None else get_checkpointer("memory")
    interrupt_nodes = ["review_validator_node"] if hitl_flag else []

    return builder.compile(
        checkpointer=active_checkpointer,
        interrupt_before=interrupt_nodes,
    )


# Convenience alias matching architecture naming
compile_graph = build_travel_planner_graph
