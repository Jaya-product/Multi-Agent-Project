"""Main Streamlit application entry point for the Dubai AI Travel Planning System."""

import os
import sys
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from configs.settings import get_settings, AppSettings
from src.graph.builder import build_travel_planner_graph
from src.graph.state import create_initial_state
from src.utils.profiler import ExecutionProfiler
from src.models.request import UserTravelRequest
from src.models.itinerary import FinalItineraryPlan

from app.components.itinerary_view import render_itinerary_view
from app.components.budget_charts import (
    render_budget_summary_cards,
    render_budget_breakdown_chart,
    render_daily_spend_bar_chart,
    render_alternatives_view,
)
from app.components.map_view import render_route_map
from app.components.trace_viewer import render_trace_viewer, render_progress_stepper
from app.components.profiler_view import render_profiler_view
from data.build_seed_db import build_database_if_missing

# Ensure database exists across all deployment environments (Docker, Streamlit Cloud, Bare Metal)
build_database_if_missing()

# Page Configuration
st.set_page_config(
    page_title="Dubai AI Travel Planner — Multi-Agent Studio",
    page_icon="🇦🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_custom_css():
    """Load custom CSS styling file."""
    css_path = Path(__file__).parent / "styles" / "custom.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_custom_css()


# Initialize Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "graph_app" not in st.session_state:
    st.session_state.graph_app = None
if "final_plan" not in st.session_state:
    st.session_state.final_plan = None
if "node_traces" not in st.session_state:
    st.session_state.node_traces = []
if "review_result" not in st.session_state:
    st.session_state.review_result = None
if "error_log" not in st.session_state:
    st.session_state.error_log = []
if "revision_count" not in st.session_state:
    st.session_state.revision_count = 0
if "is_paused" not in st.session_state:
    st.session_state.is_paused = False
if "paused_state" not in st.session_state:
    st.session_state.paused_state = None
if "profiler" not in st.session_state:
    st.session_state.profiler = None
if "user_prompt_text" not in st.session_state:
    st.session_state.user_prompt_text = (
        "Plan a 4-day trip to Dubai with a budget of AED 5,000, excluding flights. "
        "I enjoy cultural attractions, local food, and beaches. "
        "I prefer affordable hotels and want to avoid crowded places."
    )


# Curated UX Travel Personas
PRESETS = [
    {
        "id": "cultural",
        "icon": "🏛️",
        "title": "Cultural Explorer",
        "days": 4,
        "budget": 4500,
        "hotel": "budget",
        "pace": "moderate",
        "tagline": "Historical souks in Deira & Bur Dubai, Creek abra rides, traditional cuisine & local heritage.",
        "prompt": (
            "Plan a 4-day trip to Dubai with a budget of AED 4,500. "
            "I am interested in authentic culture, historical souks in Deira and Bur Dubai, "
            "traditional dining, and local heritage. Please keep pace moderate and avoid crowded places."
        ),
    },
    {
        "id": "luxury",
        "icon": "✨",
        "title": "Luxury Coast & Skyline",
        "days": 3,
        "budget": 12000,
        "hotel": "luxury",
        "pace": "relaxed",
        "tagline": "Fine dining, Palm Jumeirah beach clubs, Burj Al Arab views & 5-star hotel luxury standards.",
        "prompt": (
            "3-day luxury getaway to Dubai with an AED 12,000 budget. "
            "Focus on fine dining, beach clubs in Jumeirah and Palm Jumeirah, "
            "scenic sightseeing, and 5-star hotel standards with a relaxed pace."
        ),
    },
    {
        "id": "family",
        "icon": "👨‍👩‍👧",
        "title": "Family Fun & Parks",
        "days": 5,
        "budget": 7500,
        "hotel": "midscale",
        "pace": "moderate",
        "tagline": "Family-friendly Dubai Mall, indoor theme parks, public beaches & comfortable metro transit.",
        "prompt": (
            "5-day family-friendly Dubai trip on a budget of AED 7,500. "
            "Focus on sightseeing, indoor theme parks, public beaches, and diverse casual dining. "
            "Moderate pace and comfortable transport."
        ),
    },
    {
        "id": "budget",
        "icon": "🏄",
        "title": "Budget Adventure & Souks",
        "days": 3,
        "budget": 2800,
        "hotel": "budget",
        "pace": "moderate",
        "tagline": "Solo explorer on a tight budget: public beaches, street food dining, RTA Metro rides & free sights.",
        "prompt": (
            "3 days in Dubai for a solo traveler with a tight budget of AED 2,800. "
            "I want beaches, outdoor sights, street food dining, and budget hotel lodging. Avoid luxury."
        ),
    },
]

PROMPT_PRESETS = {"— Select a quick preset or type custom request —": ""}
for p in PRESETS:
    PROMPT_PRESETS[f"{p['icon']} {p['title']} ({p['days']} Days, AED {p['budget']:,})"] = p["prompt"]


# =====================================================================
# Sidebar: User Controls & Ergonomics
# =====================================================================
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=600&auto=format&fit=crop&q=80",
        caption="Dubai, United Arab Emirates",
        use_container_width=True,
    )
    st.title("Trip Configuration")

    # Preset selection
    preset_choice = st.selectbox("Sample Prompt Templates:", list(PROMPT_PRESETS.keys()))
    if preset_choice != "— Select a quick preset or type custom request —":
        st.session_state.user_prompt_text = PROMPT_PRESETS[preset_choice]

    # Prompt text area
    user_prompt = st.text_area(
        "Travel Request Prompt:",
        value=st.session_state.user_prompt_text,
        height=130,
        help="Specify your trip duration, budget, preferred pace, interests, and hotel tier.",
    )
    st.session_state.user_prompt_text = user_prompt

    st.markdown("---")
    st.subheader("Fine-Tune Parameters")

    # Sliders and selectors
    budget_aed = st.slider("Total Budget (AED):", min_value=1000, max_value=25000, value=5000, step=500)
    duration_days = st.slider("Trip Duration (Days):", min_value=1, max_value=7, value=4, step=1)

    col_h, col_p = st.columns(2)
    with col_h:
        hotel_tier = st.selectbox("Hotel Tier:", ["budget", "midscale", "luxury"], index=0)
    with col_p:
        pace = st.selectbox("Pace:", ["moderate", "relaxed", "fast-paced"], index=0)

    interests = st.multiselect(
        "Key Interests:",
        options=["culture", "beach", "dining", "sightseeing", "shopping", "adventure"],
        default=["culture", "dining", "beach"],
    )

    avoid_crowds = st.checkbox("Avoid Crowded Venues", value=True)

    if st.button("✨ Sync Prompt with Sliders", help="Generate prompt text from above slider parameters", use_container_width=True):
        crowd_clause = "Avoid crowded places." if avoid_crowds else ""
        synced_prompt = (
            f"Plan a {duration_days}-day trip to Dubai with a budget of AED {budget_aed:,}, excluding flights. "
            f"I enjoy {', '.join(interests)}. I prefer a {hotel_tier} hotel with a {pace} pace. {crowd_clause}"
        )
        st.session_state.user_prompt_text = synced_prompt
        st.rerun()

    st.markdown("---")
    st.subheader("Multi-Agent Runtime")

    providers = ["groq", "google", "openai", "ollama"]
    google_key_valid = (os.getenv("GOOGLE_API_KEY") or "").startswith("AIzaSy")
    groq_key_valid = bool(os.getenv("GROQ_API_KEY"))

    default_prov = "google" if google_key_valid else ("groq" if groq_key_valid else "groq")
    prov_idx = providers.index(default_prov) if default_prov in providers else 0

    llm_provider = st.selectbox("LLM Provider:", providers, index=prov_idx)
    default_model = {
        "groq": "llama-3.3-70b-versatile",
        "google": "gemini-1.5-flash",
        "openai": "gpt-4o",
        "ollama": "llama3",
    }.get(llm_provider, "llama-3.3-70b-versatile")
    model_name = st.text_input("Model Name:", value=default_model)

    with st.expander("🔑 API Key Configuration", expanded=not (google_key_valid or groq_key_valid)):
        st.caption("Enter key here if not pre-configured in Streamlit Secrets or environment variables.")
        if llm_provider == "groq":
            custom_groq = st.text_input("Groq API Key:", type="password", value=os.getenv("GROQ_API_KEY", ""), key="groq_input_key")
            if custom_groq:
                os.environ["GROQ_API_KEY"] = custom_groq
        elif llm_provider == "google":
            custom_google = st.text_input("Google AI Studio Key:", type="password", value=os.getenv("GOOGLE_API_KEY", ""), key="google_input_key")
            if custom_google:
                os.environ["GOOGLE_API_KEY"] = custom_google

    enable_hitl = st.toggle(
        "Enable Human-in-the-Loop Review Gate",
        value=False,
        help="Pauses the LangGraph execution right before the Review Node to allow human inspection and override.",
    )

    st.markdown("---")
    generate_btn = st.button("🚀 Generate Travel Plan", type="primary", use_container_width=True)

    if st.button("🔄 Reset Studio State", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.final_plan = None
        st.session_state.node_traces = []
        st.session_state.review_result = None
        st.session_state.error_log = []
        st.session_state.revision_count = 0
        st.session_state.is_paused = False
        st.session_state.paused_state = None
        st.rerun()


# =====================================================================
# Main Header
# =====================================================================
st.markdown(
    """
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.8rem;">
            <div>
                <h1>🇦🇪 DUBAI AI TRAVEL PLANNER</h1>
                <p>Autonomous LangGraph Multi-Agent Engine • 100% Free Open Data Architecture • Real-Time Observability</p>
            </div>
            <div class="header-trust-bar">
                <span class="trust-chip">🤖 7 Specialized Agents</span>
                <span class="trust-chip">🚇 RTA Official Metro Fares</span>
                <span class="trust-chip">☀️ Heat-Aware Pacing</span>
                <span class="trust-chip">💸 100% Free Open Data</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =====================================================================
# Graph Execution Engine Logic
# =====================================================================
def run_workflow_stream(
    prompt_text: str,
    hitl_flag: bool,
    provider: Optional[str] = None,
    model: Optional[str] = None,
):
    """Execute the multi-agent graph with live event streaming."""
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        os.environ["LLM_MODEL_NAME"] = model

    thread_id = str(uuid.uuid4())
    st.session_state.session_id = thread_id
    config = {"configurable": {"thread_id": thread_id}}

    # Initialize Fresh Graph with HITL configuration
    graph = build_travel_planner_graph(enable_hitl=hitl_flag)
    st.session_state.graph_app = graph

    # Initialize State
    initial_input = create_initial_state(prompt_text)

    # Telemetry profiler
    profiler = ExecutionProfiler()
    st.session_state.profiler = profiler

    st.session_state.node_traces = []
    st.session_state.error_log = []
    st.session_state.revision_count = 0
    st.session_state.final_plan = None
    st.session_state.is_paused = False
    st.session_state.paused_state = None

    status_container = st.status("🚀 Initializing Multi-Agent Planning Graph...", expanded=True)

    try:
        for event in graph.stream(initial_input, config=config):
            for node_name, state_update in event.items():
                if node_name == "__interrupt__":
                    continue

                status_container.write(f"✓ Agent Node Executed: **`{node_name}`**")

                # Accumulate traces
                if isinstance(state_update, dict) and "node_traces" in state_update:
                    for t in state_update["node_traces"]:
                        st.session_state.node_traces.append(t)

        # Check if graph paused due to HITL interrupt
        checkpoint = graph.get_state(config)
        if checkpoint and checkpoint.next and "review_validator_node" in checkpoint.next:
            st.session_state.is_paused = True
            st.session_state.paused_state = checkpoint.values
            status_container.update(
                label="⏸️ Human-in-the-Loop Interrupt: Graph paused for user review!",
                state="running",
                expanded=True,
            )
            return

        # Complete run
        final_values = checkpoint.values if checkpoint else {}
        st.session_state.final_plan = final_values.get("final_plan")
        st.session_state.review_result = final_values.get("review_result")
        st.session_state.revision_count = final_values.get("revision_count", 0)
        st.session_state.error_log = final_values.get("error_log", [])
        st.session_state.is_paused = False

        status_container.update(label="🎉 Itinerary Generated & Validated!", state="complete", expanded=False)
        st.rerun()

    except Exception as e:
        status_container.update(label=f"❌ Execution Error: {str(e)}", state="error", expanded=True)
        st.session_state.error_log.append(str(e))
        st.error(f"❌ **Execution Error:** {str(e)}")


def resume_workflow():
    """Resume execution from paused checkpoint after human review."""
    graph = st.session_state.graph_app
    config = {"configurable": {"thread_id": st.session_state.session_id}}

    status_container = st.status("▶️ Resuming Multi-Agent Validation...", expanded=True)

    try:
        for event in graph.stream(None, config=config):
            for node_name, state_update in event.items():
                status_container.write(f"✓ Completed Node: **`{node_name}`**")
                if isinstance(state_update, dict) and "node_traces" in state_update:
                    for t in state_update["node_traces"]:
                        st.session_state.node_traces.append(t)

        checkpoint = graph.get_state(config)
        final_values = checkpoint.values if checkpoint else {}
        st.session_state.final_plan = final_values.get("final_plan")
        st.session_state.review_result = final_values.get("review_result")
        st.session_state.revision_count = final_values.get("revision_count", 0)
        st.session_state.error_log = final_values.get("error_log", [])
        st.session_state.is_paused = False
        st.session_state.paused_state = None

        status_container.update(label="🎉 Validated Itinerary Ready!", state="complete", expanded=False)
        st.rerun()

    except Exception as e:
        status_container.update(label=f"❌ Resume Error: {str(e)}", state="error", expanded=True)
        st.session_state.error_log.append(str(e))
        st.error(f"❌ **Resume Error:** {str(e)}")


# Trigger execution when user clicks button
if generate_btn:
    run_workflow_stream(
        st.session_state.user_prompt_text,
        enable_hitl,
        provider=llm_provider,
        model=model_name,
    )


# =====================================================================
# Human-in-the-Loop Interactive Review Card (if paused)
# =====================================================================
if st.session_state.is_paused and st.session_state.paused_state:
    paused = st.session_state.paused_state
    draft_budget = paused.get("budget_summary")
    draft_days = paused.get("daily_schedules", [])
    draft_hotel = paused.get("selected_hotel_zone", {})

    st.markdown(
        """
        <div class="hitl-banner">
            <div class="hitl-title">⏸️ Human-in-the-Loop Review Gate (LangGraph Interrupt)</div>
            The multi-agent workflow has drafted your candidate schedule and estimated expenses. 
            Inspect the proposed plan below. You can approve to proceed to automated QA validation, or adjust constraints.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔍 Inspect Draft Schedule & Financial Baseline", expanded=True):
        if draft_budget:
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.metric("Draft Total Cost", f"AED {draft_budget.total_cost:,.1f}")
            with col_b2:
                st.metric("Budget Ceiling", f"AED {draft_budget.budget_limit:,.1f}")
            with col_b3:
                st.metric(
                    "Draft Status",
                    "Compliant" if draft_budget.is_compliant else "Exceeds Budget",
                    delta=f"Variance: AED {draft_budget.variance_aed:,.1f}",
                )

        if draft_hotel:
            st.info(f"🏨 **Selected Hotel Zone:** {draft_hotel.get('neighborhood', 'Downtown')} (Metro Accessible: {'Yes' if draft_hotel.get('metro_accessible') else 'No'})")

        st.markdown(f"**Draft Schedule ({len(draft_days)} Days Scheduled):**")
        for d in draft_days:
            st.markdown(
                f"- **Day {d.day_number} ({d.focus_area}):** Morning: *{d.morning_activity.name}* | Lunch: *{d.lunch_spot.name}* | PM: *{d.afternoon_activity.name}* | Evening: *{d.evening_activity.name}* (Day Cost: AED {d.day_cost_aed:,.1f})"
            )

    btn_col1, btn_col2 = st.columns([1, 4])
    with btn_col1:
        if st.button("✅ Approve & Resume", type="primary"):
            resume_workflow()
            st.rerun()
    with btn_col2:
        if st.button("❌ Cancel & Reset"):
            st.session_state.is_paused = False
            st.session_state.paused_state = None
            st.rerun()


# =====================================================================
# Main Workspace Tabs
# =====================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 1. Final Itinerary Plan",
    "🔍 2. Graph Node Trace Viewer",
    "🗺️ 3. Map & Route Visualizer",
    "⚡ 4. Performance & Profiler",
])

plan: Optional[FinalItineraryPlan] = st.session_state.final_plan

# --- TAB 1: FINAL ITINERARY PLAN ---
with tab1:
    if plan:
        # Top financial KPI bar
        render_budget_summary_cards(plan.budget_breakdown)
        st.markdown("<br/>", unsafe_allow_html=True)

        # Main itinerary view
        render_itinerary_view(plan)

        st.markdown("---")
        # Visual charts
        st.subheader("📊 Financial Breakdown & Progression")
        chart_col1, chart_col2 = st.columns([1, 1])
        with chart_col1:
            donut_fig = render_budget_breakdown_chart(plan.budget_breakdown)
            st.plotly_chart(donut_fig, use_container_width=True)
        with chart_col2:
            bar_fig = render_daily_spend_bar_chart(plan.days)
            st.plotly_chart(bar_fig, use_container_width=True)

        # Alternatives
        if plan.alternatives:
            st.markdown("---")
            render_alternatives_view(plan.alternatives)

    else:
        # UX Launchpad: Interactive Persona Cards
        st.markdown(
            """
            <div class="launchpad-container">
                <div class="launchpad-header">
                    <h2>✨ Plan Your Personalized Dubai Experience</h2>
                    <p>
                        Choose a curated trip persona below to launch the autonomous multi-agent planning workflow,
                        or customize your own itinerary prompt and parameters in the sidebar.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        p_cols = st.columns(4)
        for idx, preset in enumerate(PRESETS):
            with p_cols[idx]:
                card_html = f"""
                <div class="persona-card">
                    <div>
                        <div class="persona-icon-badge">{preset['icon']}</div>
                        <div class="persona-title">{preset['title']}</div>
                        <div class="persona-tagline">{preset['tagline']}</div>
                        <div class="persona-meta-strip">
                            <span class="meta-chip" style="font-weight:700;">🗓️ {preset['days']} Days</span>
                            <span class="meta-chip" style="font-weight:700; color:#92400e; background:#fef3c7;">💰 AED {preset['budget']:,}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(f"🚀 Plan {preset['title']}", key=f"btn_persona_{idx}", use_container_width=True):
                    st.session_state.user_prompt_text = preset["prompt"]
                    run_workflow_stream(
                        preset["prompt"],
                        enable_hitl,
                        provider=llm_provider,
                        model=model_name,
                    )
                    st.rerun()


# --- TAB 2: GRAPH NODE TRACE VIEWER ---
with tab2:
    render_trace_viewer(
        node_traces=st.session_state.node_traces,
        review_result=st.session_state.review_result,
        error_log=st.session_state.error_log,
        revision_count=st.session_state.revision_count,
    )


# --- TAB 3: MAP & ROUTE VISUALIZER ---
with tab3:
    if plan and plan.days:
        render_route_map(plan.days)
    else:
        st.info("Map will render once an itinerary has been generated.")


# --- TAB 4: PERFORMANCE & PROFILER ---
with tab4:
    render_profiler_view(
        metrics=None,
        node_traces=st.session_state.node_traces,
        plan=plan,
    )
