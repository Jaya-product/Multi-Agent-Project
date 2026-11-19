"""Performance profiling, token analytics, and observability dashboard."""

from typing import List, Dict, Any, Optional
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.models.metrics import GraphExecutionMetrics, NodeExecutionMetric
from src.models.itinerary import FinalItineraryPlan


def render_profiler_view(
    metrics: Optional[GraphExecutionMetrics] = None,
    node_traces: Optional[List[Dict[str, Any]]] = None,
    plan: Optional[FinalItineraryPlan] = None,
):
    """Render comprehensive performance and telemetry metrics."""
    st.subheader("⚡ Performance & Telemetry Profiler")
    st.caption("Deep-dive observability into agent latency, token economics, and multi-agent health.")

    # High-level KPIs
    total_latency = metrics.total_latency_seconds if metrics else sum(t.get("latency_seconds", 0) for t in (node_traces or []))
    revision_count = metrics.revision_count if metrics else 0
    budget_compliant = metrics.budget_compliant if metrics else (plan.budget_breakdown.is_compliant if plan else True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Wall Latency", f"{total_latency:.2f} s")
    with col2:
        st.metric("Revision Cycles", f"{revision_count}")
    with col3:
        st.metric("Budget Compliance", "100%" if budget_compliant else "Non-compliant")
    with col4:
        # Calculate total tokens if metrics has them
        tot_tokens = sum((m.tokens_input + m.tokens_output) for m in (metrics.node_metrics if metrics else []))
        tot_cost = sum(m.estimated_cost_usd for m in (metrics.node_metrics if metrics else []))
        st.metric("Estimated LLM Cost", f"${tot_cost:.4f}", f"{tot_tokens:,} tokens")

    st.markdown("---")

    # Latency Breakdown Chart
    st.markdown("### ⏱️ Node Latency Breakdown")
    node_names = []
    latencies = []

    if node_traces:
        for t in node_traces:
            node_names.append(t.get("node_name", "Unknown"))
            latencies.append(t.get("latency_seconds", 0.0))

    if node_names:
        fig_lat = go.Figure(
            go.Bar(
                x=latencies,
                y=node_names,
                orientation="h",
                marker=dict(color="#0284c7", line=dict(color="#0369a1", width=1.5)),
                text=[f"{l:.3f}s" for l in latencies],
                textposition="auto",
                textfont=dict(color="#ffffff", size=12, family="sans-serif"),
            )
        )
        fig_lat.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=dict(
                text="<b>Execution Latency per Agent Node (Seconds)</b>",
                font=dict(size=16, color="#0f172a", family="sans-serif"),
            ),
            xaxis=dict(
                title=dict(text="Latency (seconds)", font=dict(color="#0f172a", size=13)),
                tickfont=dict(color="#334155", size=12),
                gridcolor="#e2e8f0",
            ),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(color="#0f172a", size=12, family="sans-serif"),
            ),
            height=320,
            margin=dict(l=20, r=20, t=45, b=30),
        )
        st.plotly_chart(fig_lat, use_container_width=True)
    else:
        st.info("No latency data available.")

    # Data Provenance Distribution
    if plan:
        st.markdown("### 🏷️ Data Provenance & Trust Matrix")
        st.markdown("<div style='font-size: 0.9rem; color: #475569; margin-bottom: 1rem;'>Distribution of data sources powering the final itinerary recommendations.</div>", unsafe_allow_html=True)

        source_counts: Dict[str, int] = {}
        for day in plan.days:
            # Activities
            for act in [day.morning_activity, day.lunch_spot, day.afternoon_activity, day.evening_activity]:
                src = act.cost_source.value if hasattr(act.cost_source, "value") else str(act.cost_source)
                source_counts[src] = source_counts.get(src, 0) + 1
            # Transit
            for trans in day.transit_connections:
                src = trans.fare_source.value if hasattr(trans.fare_source, "value") else str(trans.fare_source)
                source_counts[src] = source_counts.get(src, 0) + 1

        if source_counts:
            col_prov1, col_prov2 = st.columns([1, 1])
            with col_prov1:
                prov_fig = px.pie(
                    names=list(source_counts.keys()),
                    values=list(source_counts.values()),
                    title="<b>Information Provenance Ratio</b>",
                    hole=0.45,
                    color_discrete_sequence=["#10b981", "#3b82f6", "#14b8a6", "#8b5cf6", "#f97316", "#f59e0b"],
                )
                prov_fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    title=dict(font=dict(color="#0f172a", size=16)),
                    legend=dict(font=dict(color="#334155", size=12)),
                    height=300,
                    margin=dict(l=10, r=10, t=45, b=10),
                )
                st.plotly_chart(prov_fig, use_container_width=True)

            with col_prov2:
                st.markdown(
                    """
                    <div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-radius: 10px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-top: 1.75rem;">
                        <b style="font-size: 1.05rem; color: #0f172a;">Provenance Verifiability Highlights:</b>
                        <ul style="margin-top: 0.75rem; padding-left: 1.25rem; color: #334155; line-height: 1.7; font-size: 0.92rem;">
                            <li><b style="color: #0f172a;"><code>seed_database</code></b>: 100% curated local SQLite records verified against official Dubai listings.</li>
                            <li><b style="color: #0f172a;"><code>rta_official</code></b>: Direct fare calculations derived from Dubai RTA Metro/Bus zoning matrices.</li>
                            <li><b style="color: #0f172a;"><code>open_meteo</code></b>: Unmetered open weather forecast readings.</li>
                            <li><b style="color: #0f172a;"><code>osrm_routing</code></b>: Open Source Routing Machine calculated road distances & transit times.</li>
                            <li><b style="color: #15803d;">Zero Commercial APIs:</b> 100% free open-source data architecture.</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
