"""Graph execution trace inspector, deterministic audit scorecard, and state mutation viewer."""

import json
from typing import List, Dict, Any, Optional
import streamlit as st
from src.models.review import ReviewResult


NODE_SEQUENCE = [
    ("parse_requirements_node", "1. Orchestrator", "🎯"),
    ("destination_research_node", "2. Destination Research", "🔍"),
    ("logistics_routing_node", "3. Logistics & Routing", "🗺️"),
    ("budget_calculator_node", "4. Budget Calculator", "💰"),
    ("review_validator_node", "5. Review & QA", "🛡️"),
    ("revision_dispatcher_node", "6. Revision Dispatcher", "🔁"),
    ("synthesize_final_plan_node", "7. Final Synthesis", "📋"),
]


def render_progress_stepper(executed_node_names: List[str]):
    """Render horizontal pill bar showing multi-agent workflow progression."""
    st.markdown("#### 🔄 Multi-Agent Pipeline Execution Ribbon")

    pills_html = []
    for node_id, display_label, icon in NODE_SEQUENCE:
        if node_id in executed_node_names:
            cls = "step-completed"
            status_icon = "✓"
        else:
            cls = "step-pending"
            status_icon = "○"
        pills_html.append(f'<span class="step-pill {cls}">{status_icon} {icon} {display_label}</span>')

    full_stepper_html = f'<div class="workflow-stepper">{"".join(pills_html)}</div>'
    st.markdown(full_stepper_html, unsafe_allow_html=True)


def render_audit_scorecard(review_result: Optional[ReviewResult], revision_count: int = 0):
    """Render high-level deterministic constraint audit scorecard."""
    st.markdown("#### 🛡️ Deterministic QA Constraint Scorecard")
    
    is_approved = review_result.approved if review_result else True
    iterations = review_result.iteration if review_result else 1
    violations = review_result.violations if review_result else []

    budget_status = "✅ Compliant" if not any("budget" in v.lower() for v in violations) else "❌ Over Budget"
    spatial_status = "✅ Clustered" if not any("spatial" in v.lower() or "distance" in v.lower() for v in violations) else "⚠️ Adjusted"
    pacing_status = "✅ Optimal" if not any("pace" in v.lower() or "duration" in v.lower() for v in violations) else "⚠️ High Density"
    loop_status = f"{revision_count} Revisions" if revision_count > 0 else "Direct Pass (0 Loops)"

    scorecard_html = f"""
    <div class="audit-scorecard">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem;">
            <b style="font-size:1.1rem; color:#0f172a;">Audit Verification Result (Iteration {iterations})</b>
            <span class="meta-chip" style="background:{'#dcfce7' if is_approved else '#fee2e2'}; color:{'#14532d' if is_approved else '#991b1b'}; font-weight:800;">
                {'✅ APPROVED BY QA VALIDATOR' if is_approved else '⚠️ CONDITIONAL SYNTHESIS'}
            </span>
        </div>
        <div class="audit-grid">
            <div class="audit-item">
                <span class="audit-item-label">💰 Budget Limit Cap</span>
                <span class="audit-item-status {'audit-pass' if '✅' in budget_status else 'audit-warn'}">{budget_status}</span>
            </div>
            <div class="audit-item">
                <span class="audit-item-label">🗺️ Geographic Feasibility</span>
                <span class="audit-item-status {'audit-pass' if '✅' in spatial_status else 'audit-warn'}">{spatial_status}</span>
            </div>
            <div class="audit-item">
                <span class="audit-item-label">⚡ Daily Pacing & Duration</span>
                <span class="audit-item-status {'audit-pass' if '✅' in pacing_status else 'audit-warn'}">{pacing_status}</span>
            </div>
            <div class="audit-item">
                <span class="audit-item-label">🔁 Self-Correction Engine</span>
                <span class="audit-item-status audit-pass">🔄 {loop_status}</span>
            </div>
        </div>
    </div>
    """
    st.markdown(scorecard_html, unsafe_allow_html=True)


def render_trace_viewer(
    node_traces: List[Dict[str, Any]],
    review_result: Optional[ReviewResult] = None,
    error_log: Optional[List[str]] = None,
    revision_count: int = 0,
):
    """Render comprehensive multi-agent trace inspector and audit feedback."""
    executed_names = [t.get("node_name") for t in node_traces if t.get("node_name")]
    render_progress_stepper(executed_names)

    # QA Scorecard
    if review_result or node_traces:
        render_audit_scorecard(review_result, revision_count)

    if review_result and not review_result.approved and review_result.violations:
        st.error(
            f"❌ **Review Violations Detected (Iteration {review_result.iteration}):**\n"
            + "\n".join([f"- `{v}`" for v in review_result.violations])
        )
        if review_result.revision_instructions:
            st.info(f"**Actionable Revision Instructions:**\n{review_result.revision_instructions}")

    # Error logs if present
    if error_log:
        with st.expander("⚠️ System & Warning Logs", expanded=False):
            for err in error_log:
                st.code(err)

    # Detailed node traces
    st.subheader(f"🔍 Step-by-Step Node Execution Traces ({len(node_traces)} events)")
    st.markdown("<div style='font-size: 0.9rem; color: #475569; margin-bottom: 1rem;'>Inspect runtime latency, state mutations, and tool execution details for each agent node.</div>", unsafe_allow_html=True)

    if not node_traces:
        st.info("No execution traces recorded yet. Run the workflow to inspect live traces.")
        return

    for idx, trace in enumerate(node_traces):
        node_name = trace.get("node_name", f"Step {idx+1}")
        latency = trace.get("latency_seconds", 0.0)
        status = trace.get("status", "SUCCESS")
        details = trace.get("details", {})

        icon = "🟢" if status == "SUCCESS" else "🟡"
        expander_title = f"{icon} Step {idx+1}: {node_name}  —  {latency:.3f}s ({status})"

        with st.expander(expander_title, expanded=(idx == len(node_traces) - 1)):
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown(f"**Node Name:** `{node_name}`")
                st.markdown(f"**Execution Latency:** <span class='meta-chip' style='color:#0369a1;background:#e0f2fe;font-weight:700;'>⏱️ {latency:.3f}s</span>", unsafe_allow_html=True)
            with col2:
                status_color = "#15803d" if status == "SUCCESS" else "#b45309"
                status_bg = "#dcfce7" if status == "SUCCESS" else "#fef3c7"
                st.markdown(f"**Status:** <span class='meta-chip' style='color:{status_color};background:{status_bg};font-weight:700;'>{status}</span>", unsafe_allow_html=True)
                timestamp = trace.get("timestamp")
                if timestamp:
                    st.markdown(f"**Timestamp:** `{str(timestamp)}`")

            st.markdown("---")
            st.markdown("**Node State Mutations & Output Details:**")
            st.json(details if details else {"message": "No structured details payload captured."})
