# Multi-Agent Execution Playbook & Runtime Lifecycle
## Dubai AI Travel Planning System (LangGraph Engine)

---

## 1. Overview & Purpose

This **Playbook** defines the operational execution flow of the Dubai AI Travel Planning System. It documents how the LangGraph multi-agent pipeline is invoked, how state transitions through each specialized agent node, how parallel worker branches are triggered via the `Send` API, and how feedback revision loops operate.

It serves as the definitive reference for developers and engineers building, testing, and debugging the multi-agent graph.

---

## 2. End-to-End System Execution Sequence

This sequence diagram illustrates the complete execution flow from the initial natural-language user prompt in Streamlit to the final rendered itinerary, highlighting parallel execution and conditional review loops.

```mermaid
sequenceDiagram
    autonumber
    actor User as Traveler (Streamlit UI)
    participant UI as Streamlit Controller
    participant Graph as Compiled StateGraph
    participant State as TravelPlanState (RAM)
    participant Orch as parse_requirements_node
    participant Dest as destination_research_node
    participant Log as logistics_routing_node
    participant DB as SQLite DB & Tools Layer
    participant Bud as budget_calculator_node
    participant Rev as review_validator_node
    participant Disp as revision_dispatcher_node
    participant Synth as synthesize_final_plan_node

    User->>UI: Enters Prompt & Clicks "Generate Plan"
    UI->>Graph: invoke(initial_state, thread_config)
    Graph->>State: Initialize State (raw_prompt, revision_count=0)
    
    %% Phase 1: Parse
    Graph->>Orch: Execute parse_requirements_node(state)
    Orch->>State: Write user_request (Pydantic model)
    
    %% Phase 2: Parallel Fan-Out
    Note over Graph,Log: Parallel Fan-Out via Send API
    par Parallel Exploration Branch
        Graph->>Dest: Send("destination_research_node", state)
        Dest->>DB: search_attractions(category, crowd)
        Dest->>DB: search_restaurants(cuisine, price_tier)
        DB-->>Dest: POIs & Dining venues
        Dest->>State: Append candidate_attractions, candidate_dining (operator.add)
    and
        Graph->>Log: Send("logistics_routing_node", state)
        Log->>DB: get_neighborhood_zones(tier)
        Log->>DB: calculate_transit_route(RTA matrix / OSRM)
        DB-->>Log: Hotel zones & transit segments
        Log->>State: Store selected_hotel_zone & daily_schedules
    end
    
    %% Phase 3: Synchronization & Budgeting
    Note over State,Bud: State Synchronizer merges parallel list branches
    Graph->>Bud: Execute budget_calculator_node(state)
    Bud->>DB: compute_budget_breakdown()
    alt Budget Exceeded
        Bud->>DB: suggest_alternatives()
        Bud->>State: Store alternative_options[]
    end
    Bud->>State: Store budget_summary
    
    %% Phase 4: Quality Review & Validation
    Graph->>Rev: Execute review_validator_node(state)
    Rev->>DB: verify_constraints_rule_engine(state)
    DB-->>Rev: Validation results (budget, pacing, transit, prefs)
    
    alt Validation Fails (Violations & revision_count < 3)
        Rev->>State: Store review_result (approved=False, violations)
        Graph->>Disp: route_review_verdict -> revision_dispatcher_node
        Disp->>State: Increment revision_count += 1 & format feedback
        
        alt Budget Issue
            Disp->>Bud: route_revision_target -> budget_calculator_node
        else Spatial / Pacing Issue
            Disp->>Log: route_revision_target -> logistics_routing_node
        else Preference Missing
            Disp->>Dest: route_revision_target -> destination_research_node
        end
        Note over Graph,Rev: Re-work executed, returns back through review
        
    else Validation Passes (or revision_count >= 3)
        Rev->>State: Store review_result (approved=True)
        Graph->>Synth: route_review_verdict -> synthesize_final_plan_node
        Synth->>State: Assemble FinalItineraryPlan
        Graph-->>UI: Return Final State Output
        UI-->>User: Render Day-by-Day Cards, Route Map & Budget Chart
    end
```

---

## 3. Deep-Dive: Parallel Agent Fan-Out & State Reducers

A primary capability of LangGraph is dynamic concurrency using the **`Send` API**. Instead of executing destination research and logistics sequentially, the graph forks both nodes into concurrent worker threads.

### Parallel Fan-Out Architecture

```mermaid
flowchart TD
    Parse["1. parse_requirements_node\n(Extracts user constraints)"] --> Router{"parallel_exploration_router\n(Conditional Edge Function)"}
    
    Router -->|Send API Payload 1| DestWorker["destination_research_node\n[Worker Thread A]"]
    Router -->|Send API Payload 2| LogWorker["logistics_routing_node\n[Worker Thread B]"]
    
    subgraph Worker_A ["Worker Thread A: Destination Discovery"]
        DestWorker --> T1["Tool: search_attractions()"]
        DestWorker --> T2["Tool: search_restaurants()"]
        DestWorker --> T3["Tool: get_weather_forecast()"]
    end
    
    subgraph Worker_B ["Worker Thread B: Spatial Routing"]
        LogWorker --> T4["Tool: get_neighborhood_zones()"]
        LogWorker --> T5["Tool: calculate_transit_route()"]
    end
    
    T1 --> Reducer{{"State Reducer Junction\nAnnotated[List, operator.add]"}}
    T2 --> Reducer
    T4 --> Reducer
    T5 --> Reducer
    
    Reducer --> SyncState["Synchronized TravelPlanState\n(Merged Lists & Dictionaries)"]
    SyncState --> BudgetNode["4. budget_calculator_node"]
```

### State Reducer Implementation Pattern

When two nodes run in parallel and both write to state, LangGraph requires an **annotated reducer** to prevent `INVALID_CONCURRENT_GRAPH_UPDATE` exceptions.

```python
from typing import TypedDict, Annotated, List, Dict, Any
import operator
from langgraph.types import Send

# 1. State definition with reducers for parallel writes
class TravelPlanState(TypedDict):
    user_request: UserTravelRequest
    # operator.add ensures parallel appends are merged, not overwritten
    candidate_attractions: Annotated[List[ActivityItem], operator.add]
    candidate_dining: Annotated[List[ActivityItem], operator.add]
    selected_hotel_zone: Dict[str, Any]
    daily_schedules: List[DailyPlan]
    ...

# 2. Router returning Send objects
def parallel_exploration_router(state: TravelPlanState) -> List[Send]:
    """Dynamically spawns parallel nodes with isolated state contexts."""
    return [
        Send("destination_research_node", state),
        Send("logistics_routing_node", state)
    ]
```

---

## 4. Deep-Dive: Self-Correction & Feedback Revision Loop

When the **Review Node** flags one or more constraint violations (e.g., budget exceeded, excessive travel time between activities, missing cultural spots), it triggers the **Revision Dispatcher**.

```mermaid
sequenceDiagram
    autonumber
    participant State as TravelPlanState
    participant Rev as review_validator_node
    participant Rule as verify_constraints_rule_engine
    participant Edge as route_review_verdict (Router)
    participant Disp as revision_dispatcher_node
    participant Target as Offending Node (Dest / Log / Budget)

    Rev->>Rule: Execute deterministic 5-rule check
    Rule-->>Rev: Violations detected: ["OVER_BUDGET: AED +620", "EXCESSIVE_TRANSIT: Day 2 > 50min"]
    Rev->>State: review_result.approved = False
    Rev->>State: review_result.violations = ["OVER_BUDGET", "EXCESSIVE_TRANSIT"]
    
    Rev->>Edge: Trigger conditional edge
    Edge->>Edge: Check revision_count (e.g., 0 < 3)
    Edge->>Disp: Route to revision_dispatcher_node
    
    Disp->>State: Increment revision_count (0 -> 1)
    Disp->>Disp: Inspect violation priorities (Budget > Pacing > Preference)
    Disp->>State: Inject revision_instructions ("Swap Day 2 afternoon activity for lower cost venue")
    
    Disp->>Target: Dispatch targeted re-work
    Note over Target: Node re-executes with corrective instructions
    Target->>State: Update candidate / schedule state
    Target->>Rev: Re-enter validation gate
```

### Edge Decision Matrix

| Condition | `revision_count` | Router Verdict | Next Target Node |
| :--- | :--- | :--- | :--- |
| `approved == True` | Any | `synthesize_final_plan_node` | UI Assembly |
| `approved == False` | $< 3$ | `revision_dispatcher_node` | Budget, Logistics, or Destination Node |
| `approved == False` | $\ge 3$ (Hard Cap) | `synthesize_final_plan_node` | UI Assembly (with `[PARTIAL_VALIDATION]` badge) |

---

## 5. Human-in-the-Loop Interrupt & Resume Lifecycle

For interactive control, the system can pause execution right after budget estimation, giving travelers the opportunity to inspect intermediate drafts before final review.

```mermaid
sequenceDiagram
    autonumber
    actor User as Traveler (Streamlit UI)
    participant UI as Streamlit Session
    participant Graph as LangGraph Engine
    participant Checkpoint as MemorySaver Storage
    participant Node as review_validator_node

    User->>UI: Clicks "Generate Trip Plan" (HITL toggle ON)
    UI->>Graph: invoke(state, config={"configurable": {"thread_id": "session_123"}})
    
    Note over Graph: Graph executes Nodes 1 -> 2 & 3 -> 4
    Graph->>Checkpoint: Auto-saves state after budget_calculator_node
    
    Note over Graph: interrupt_before=["review_validator_node"] triggered!
    Graph-->>UI: Graph Execution Paused (Yields Control)
    
    UI-->>User: Displays "Draft Review & Customization" Card
    Note over User,UI: User swaps a restaurant or increases budget
    
    User->>UI: Clicks "Approve & Resume"
    UI->>Graph: invoke(Command(resume=user_override_data), config={"configurable": {"thread_id": "session_123"}})
    
    Graph->>Checkpoint: Load state for "session_123" and apply overrides
    Graph->>Node: Resume execution into review_validator_node
    Note over Graph: Graph finishes validation and synthesis
    Graph-->>UI: Return Final Structured Itinerary
    UI-->>User: Render Full Itinerary & Charts
```

---

## 6. Node-by-Node State Mutation Reference

This table outlines how the centralized `TravelPlanState` dictionary evolves through each step of the pipeline:

| Step | Executing Node | State Keys Read | State Keys Mutated | Deterministic Output Schema |
| :---: | :--- | :--- | :--- | :--- |
| **0** | Graph Input | *(None)* | `raw_prompt`, `thread_id` | Initial dictionary |
| **1** | `parse_requirements_node` | `raw_prompt` | `user_request` | `UserTravelRequest` (Pydantic) |
| **2a**| `destination_research_node` | `user_request`, revision notes | `candidate_attractions`, `candidate_dining` | `List[ActivityItem]` (appended) |
| **2b**| `logistics_routing_node` | `user_request`, candidates | `selected_hotel_zone`, `daily_schedules` | `Dict`, `List[DailyPlan]` |
| **3** | `budget_calculator_node` | `daily_schedules`, hotel zone | `budget_summary`, `alternative_options` | `BudgetSummary`, `List[AlternativeOption]` |
| **4** | `review_validator_node` | Full state | `review_result` | `ReviewResult` (Pass/Fail) |
| **5** | `revision_dispatcher_node` | `review_result` | `revision_count`, error instructions | State counter increment |
| **6** | `synthesize_final_plan_node` | Complete validated state | `final_plan` | `FinalItineraryPlan` (Pydantic) |

---

## 7. How to Invoke the Graph Programmatically

### A. Python Headless Invocation (CLI / Script / Test)

```python
import uuid
from src.graph.builder import build_travel_planner_graph
from src.models.request import UserTravelRequest

# 1. Compile the graph
app = build_travel_planner_graph()

# 2. Setup thread ID for state checkpointing
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}

# 3. Define initial input payload
initial_input = {
    "raw_prompt": (
        "Plan a 4-day trip to Dubai with a budget of AED 5,000, excluding flights. "
        "I enjoy cultural attractions, local food, and beaches. "
        "I prefer affordable hotels and want to avoid crowded places."
    ),
    "revision_count": 0,
    "error_log": [],
    "node_traces": []
}

# 4. Stream or invoke execution
print("=== Starting LangGraph Travel Planner ===")
final_state = app.invoke(initial_input, config=config)

# 5. Access final structured deliverable
plan = final_state.get("final_plan")
print(f"Trip Title: {plan.trip_title}")
print(f"Total Cost: AED {plan.budget_breakdown.total_cost:,.2f}")
print(f"Days Scheduled: {len(plan.days)}")
```

---

### B. Streamlit Streaming & Event Inspection

```python
import streamlit as st
from src.graph.builder import build_travel_planner_graph

# Compile graph once per session
if "graph_app" not in st.session_state:
    st.session_state.graph_app = build_travel_planner_graph()

app = st.session_state.graph_app
config = {"configurable": {"thread_id": st.session_state.session_id}}

# Stream node execution events to update UI in real time
with st.status("Executing Multi-Agent Workflow...", expanded=True) as status:
    for event in app.stream(initial_input, config=config):
        for node_name, state_update in event.items():
            st.write(f"Completed node: **{node_name}**")
            # Capture intermediate state snapshots for Tab 2 (Trace Inspector)
            st.session_state.trace_logs.append({
                "node": node_name,
                "update": state_update
            })
    status.update(label="Itinerary Generation Complete!", state="complete")
```

---

## 8. Failure Handling & Recovery Protocols

| Failure Scenario | Detection Mechanism | Recovery Action | User-Facing Indication |
| :--- | :--- | :--- | :--- |
| **LLM Rate Limit (429) / Transient Error** | `tenacity` retry wrapper | Exponential backoff (3 attempts: 2s, 4s, 8s); optional failover provider | Minor execution delay notification |
| **Output JSON Malformed** | Pydantic `ValidationError` | Node re-invoked with syntax correction prompt (max 2 retries) | Transparent self-healing |
| **Budget Exceeded after 3 Cycles** | `revision_count >= 3` | Graph forces synthesis with lower-tier hotel zones & cheaper dining substitutions | Visible `[PARTIAL_VALIDATION]` warning badge in UI |
| **Weather API Network Failure** | `httpx.TimeoutException` | Default to Dubai historical seasonal average temperature | Weather context noted as `historical_baseline` |
| **OSRM Route Engine Offline** | Network connection error | Instant switch to local **Haversine formula** detour math | Transit duration tagged as `haversine_local` |
