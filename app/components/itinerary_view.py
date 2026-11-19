"""Day-by-day itinerary renderer with timeline architecture and provenance tags."""

import json
from typing import List, Dict, Any, Optional
import streamlit as st
from src.models.itinerary import FinalItineraryPlan, DailyPlan, ActivityItem, TransitSegment
from src.models.enums import DataSource


def get_provenance_badge_html(source: DataSource) -> str:
    """Generate colored HTML pill badge representing data provenance."""
    mapping = {
        DataSource.SEED_DATABASE: ("badge-seed-database", "Seed DB (Curated)"),
        DataSource.RTA_OFFICIAL: ("badge-rta-official", "RTA Official Fare"),
        DataSource.OPEN_METEO: ("badge-open-meteo", "Open-Meteo Weather"),
        DataSource.OSRM_ROUTING: ("badge-osrm-routing", "OSRM Road Route"),
        DataSource.OPEN_STREET_MAP: ("badge-open-street-map", "OpenStreetMap"),
        DataSource.LLM_ESTIMATE: ("badge-llm-estimate", "AI Estimate"),
    }
    css_class, label = mapping.get(source, ("badge-seed-database", str(source.value)))
    return f'<span class="badge-provenance {css_class}">{label}</span>'


def get_activity_item_html(slot_name: str, item: ActivityItem, dot_class: str, time_label: str) -> str:
    """Generate HTML for a single timeline activity card."""
    indoor_badge = "🏛️ Indoor (AC)" if item.is_indoor else "☀️ Outdoor"
    crowd_badge = f"👥 {item.crowd_level.capitalize()} Crowd"
    provenance_html = get_provenance_badge_html(item.cost_source)

    slot_lower = slot_name.lower()
    if "morning" in slot_lower:
        slot_class = "activity-card-morning"
    elif "lunch" in slot_lower or "dining" in slot_lower:
        slot_class = "activity-card-lunch"
    elif "afternoon" in slot_lower:
        slot_class = "activity-card-afternoon"
    else:
        slot_class = "activity-card-evening"

    return f"""
    <div class="timeline-step">
        <div class="timeline-dot {dot_class}"></div>
        <div class="activity-card {slot_class}">
            <div class="activity-header">
                <span class="activity-slot">{slot_name} &nbsp;•&nbsp; <span style="color:#64748b;font-weight:600;">{time_label}</span></span>
                <span class="activity-cost">AED {item.cost_aed:,.1f}</span>
            </div>
            <div class="activity-name">{item.name}</div>
            <div class="activity-meta">
                <span class="meta-chip">📍 {item.neighborhood}</span>
                <span class="meta-chip">⏱️ {item.duration_hours:.1f} hrs</span>
                <span class="meta-chip">🏷️ {item.category.capitalize()}</span>
                <span class="meta-chip">{indoor_badge}</span>
                <span class="meta-chip">{crowd_badge}</span>
                {provenance_html}
            </div>
        </div>
    </div>
    """


def get_transit_segment_html(segment: TransitSegment) -> str:
    """Generate HTML for a timeline transit connector."""
    mode_icons = {
        "metro": "🚇 Dubai Metro",
        "bus": "🚌 RTA Bus",
        "taxi": "🚕 Dubai Taxi",
        "walking": "🚶 Walking",
        "abra": "🛶 Dubai Creek Abra",
        "monorail": "🚝 Palm Monorail",
    }
    mode_text = mode_icons.get(segment.mode.lower(), f"🚗 {segment.mode.capitalize()}")
    provenance_html = get_provenance_badge_html(segment.fare_source)

    return f"""
    <div class="timeline-transit-wrapper">
        <div class="transit-connector">
            <span>{mode_text}: <b>{segment.origin}</b> &nbsp;➔&nbsp; <b>{segment.destination}</b></span>
            &nbsp;|&nbsp;
            <span class="transit-pill">⏱️ {segment.duration_minutes} min</span>
            &nbsp;|&nbsp;
            <span class="transit-pill">💳 AED {segment.fare_aed:,.1f}</span>
            &nbsp;{provenance_html}
        </div>
    </div>
    """


def render_activity_item(slot_name: str, item: ActivityItem):
    """Render a single activity card (backward-compatibility)."""
    st.markdown(get_activity_item_html(slot_name, item, "dot-morning", "Scheduled"), unsafe_allow_html=True)


def render_transit_segment(segment: TransitSegment):
    """Render transit connection pill between activities (backward-compatibility)."""
    st.markdown(get_transit_segment_html(segment), unsafe_allow_html=True)


def render_itinerary_view(plan: FinalItineraryPlan):
    """Render full trip plan day-by-day with interactive luxury timeline components."""
    st.markdown(f"## 🇦🇪 {plan.trip_title}")

    # Profile summary bar
    profile = plan.user_profile
    st.markdown(
        f"""
        <div style="display: flex; flex-wrap: wrap; gap: 0.65rem; margin-bottom: 1.25rem;">
            <span class="meta-chip" style="font-size: 0.9rem; padding: 6px 14px; background: #ffffff; border: 1.5px solid #cbd5e1;">🗓️ <b>Duration:</b> {profile.duration_days} Days</span>
            <span class="meta-chip" style="font-size: 0.9rem; padding: 6px 14px; background: #ffffff; border: 1.5px solid #cbd5e1;">💰 <b>Budget Target:</b> AED {profile.budget_aed:,.0f}</span>
            <span class="meta-chip" style="font-size: 0.9rem; padding: 6px 14px; background: #ffffff; border: 1.5px solid #cbd5e1;">🏨 <b>Hotel Tier:</b> {profile.hotel_tier.capitalize()}</span>
            <span class="meta-chip" style="font-size: 0.9rem; padding: 6px 14px; background: #ffffff; border: 1.5px solid #cbd5e1;">⚡ <b>Pace:</b> {profile.pace.capitalize()}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Warning badge if review summary had notes
    if not plan.review_summary.approved:
        st.warning("⚠️ **Partial Validation Notice:** Itinerary was synthesized after maximum review iterations with closest feasible constraints.")

    st.markdown("---")

    # Render each day in an expandable card with connected timeline
    for day in plan.days:
        day_cost_str = f"AED {day.day_cost_aed:,.1f}"
        with st.expander(f"📍 Day {day.day_number}: {day.focus_area}  —  ({day_cost_str})", expanded=True):
            banner_html = f"""
            <div class="day-hero-banner">
                <div class="day-hero-title">
                    <span class="day-number-pill">DAY {day.day_number}</span>
                    <span class="day-focus-label">🏙️ {day.focus_area}</span>
                </div>
                <div style="display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap;">
                    <span class="meta-chip" style="font-weight: 700;">4 Activities &nbsp;•&nbsp; {len(day.transit_connections)} Transit Legs</span>
                    <span class="day-cost-badge">{day_cost_str}</span>
                </div>
            </div>
            """

            timeline_html = '<div class="itinerary-timeline">'
            # Morning
            timeline_html += get_activity_item_html("🌅 Morning Exploration", day.morning_activity, "dot-morning", "09:00 - 12:30")
            if len(day.transit_connections) > 0:
                timeline_html += get_transit_segment_html(day.transit_connections[0])

            # Lunch
            timeline_html += get_activity_item_html("🍽️ Midday Dining", day.lunch_spot, "dot-lunch", "12:30 - 14:00")
            if len(day.transit_connections) > 1:
                timeline_html += get_transit_segment_html(day.transit_connections[1])

            # Afternoon
            timeline_html += get_activity_item_html("🌇 Afternoon Adventure", day.afternoon_activity, "dot-afternoon", "14:30 - 18:00")
            if len(day.transit_connections) > 2:
                timeline_html += get_transit_segment_html(day.transit_connections[2])

            # Evening
            timeline_html += get_activity_item_html("🌙 Evening Experience", day.evening_activity, "dot-evening", "18:30 - 21:30")
            timeline_html += '</div>'

            st.markdown(banner_html + timeline_html, unsafe_allow_html=True)

    # Export & Download Section
    st.markdown("### 📥 Export Travel Plan")
    exp_col1, exp_col2 = st.columns(2)

    # Markdown export
    md_content = generate_markdown_summary(plan)
    with exp_col1:
        st.download_button(
            label="📄 Download as Markdown",
            data=md_content,
            file_name=f"dubai_itinerary_{plan.thread_id[:8]}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # JSON export
    json_str = plan.model_dump_json(indent=2)
    with exp_col2:
        st.download_button(
            label="📦 Download Structured JSON",
            data=json_str,
            file_name=f"dubai_itinerary_{plan.thread_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
        )


def generate_markdown_summary(plan: FinalItineraryPlan) -> str:
    """Format itinerary into readable markdown document."""
    lines = [
        f"# {plan.trip_title}",
        f"**Thread ID:** `{plan.thread_id}`",
        f"**Duration:** {plan.user_profile.duration_days} Days | **Budget:** AED {plan.user_profile.budget_aed:,.0f} | **Total Spend:** AED {plan.budget_breakdown.total_cost:,.1f}",
        "",
        "## Budget Breakdown",
        f"- **Accommodation:** AED {plan.budget_breakdown.accommodation_cost:,.1f}",
        f"- **Dining:** AED {plan.budget_breakdown.dining_cost:,.1f}",
        f"- **Activities:** AED {plan.budget_breakdown.activities_cost:,.1f}",
        f"- **Transport:** AED {plan.budget_breakdown.transport_cost:,.1f}",
        f"- **Total Spend:** AED {plan.budget_breakdown.total_cost:,.1f} (Variance: AED {plan.budget_breakdown.variance_aed:,.1f})",
        "",
        "---",
        "## Daily Itinerary",
    ]

    for d in plan.days:
        lines.extend([
            f"### Day {d.day_number}: {d.focus_area} (AED {d.day_cost_aed:,.1f})",
            f"- **Morning:** {d.morning_activity.name} ({d.morning_activity.neighborhood}) - AED {d.morning_activity.cost_aed:.1f}",
            f"- **Lunch:** {d.lunch_spot.name} ({d.lunch_spot.neighborhood}) - AED {d.lunch_spot.cost_aed:.1f}",
            f"- **Afternoon:** {d.afternoon_activity.name} ({d.afternoon_activity.neighborhood}) - AED {d.afternoon_activity.cost_aed:.1f}",
            f"- **Evening:** {d.evening_activity.name} ({d.evening_activity.neighborhood}) - AED {d.evening_activity.cost_aed:.1f}",
            "",
            "**Transit Segments:**",
        ])
        for t in d.transit_connections:
            lines.append(f"  * {t.mode.upper()}: {t.origin} ➔ {t.destination} ({t.duration_minutes} min, AED {t.fare_aed:.1f})")
        lines.append("")

    return "\n".join(lines)
