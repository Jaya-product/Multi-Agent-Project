"""Plotly budget charts and financial visualization components."""

from typing import List, Optional
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from src.models.budget import BudgetSummary, AlternativeOption
from src.models.itinerary import DailyPlan


def render_budget_summary_cards(budget: BudgetSummary):
    """Render top-level financial KPI metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Planned Spend",
            value=f"AED {budget.total_cost:,.1f}",
            delta=f"Limit: AED {budget.budget_limit:,.0f}",
            delta_color="off",
        )
    with col2:
        variance = budget.variance_aed
        st.metric(
            label="Budget Variance",
            value=f"AED {abs(variance):,.1f}",
            delta="Under Budget" if variance >= 0 else "Over Budget",
            delta_color="normal" if variance >= 0 else "inverse",
        )
    with col3:
        compliance_text = "Compliant" if budget.is_compliant else "Over Budget"
        st.metric(
            label="Budget Status",
            value=compliance_text,
            delta="Verified" if budget.is_compliant else "Needs Adjustment",
            delta_color="normal" if budget.is_compliant else "inverse",
        )
    with col4:
        pct_used = (budget.total_cost / budget.budget_limit * 100) if budget.budget_limit > 0 else 0
        st.metric(
            label="Budget Utilization",
            value=f"{pct_used:.1f}%",
            delta=f"{100 - pct_used:.1f}% remaining" if pct_used <= 100 else f"{pct_used - 100:.1f}% excess",
            delta_color="normal" if pct_used <= 100 else "inverse",
        )


def render_budget_breakdown_chart(budget: BudgetSummary) -> go.Figure:
    """Create a luxury styled Plotly donut chart showing cost distribution."""
    labels = ["Accommodation", "Dining", "Activities & Sights", "Transit & Transport"]
    values = [
        budget.accommodation_cost,
        budget.dining_cost,
        budget.activities_cost,
        budget.transport_cost,
    ]
    colors = ["#d97706", "#0d9488", "#0284c7", "#7c3aed"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                textinfo="label+percent",
                insidetextorientation="radial",
                textfont=dict(size=12, color="#ffffff", family="sans-serif"),
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2.5)),
                hoverinfo="label+value+percent",
                hovertemplate="<b>%{label}</b><br>Amount: AED %{value:,.1f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title=dict(
            text="<b>Expense Allocation (AED)</b>",
            font=dict(size=17, color="#0f172a", family="sans-serif"),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(color="#334155", size=13),
        ),
        margin=dict(l=20, r=20, t=50, b=50),
        height=340,
        annotations=[
            dict(
                text=f"<span style='font-size:12px;color:#64748b;'>Total</span><br><b style='font-size:16px;color:#0f172a;'>AED {budget.total_cost:,.0f}</b>",
                x=0.5,
                y=0.5,
                font=dict(size=14, color="#0f172a"),
                showarrow=False,
            )
        ],
    )
    return fig


def render_daily_spend_bar_chart(days: List[DailyPlan]) -> go.Figure:
    """Create a bar chart showing day-by-day expense progression."""
    day_labels = [f"Day {d.day_number}" for d in days]
    activities_cost = []
    dining_cost = []
    transit_cost = []

    for d in days:
        # Activities
        act_total = d.morning_activity.cost_aed + d.afternoon_activity.cost_aed + d.evening_activity.cost_aed
        # Dining
        dine_total = d.lunch_spot.cost_aed
        # Transit
        trans_total = sum(t.fare_aed for t in d.transit_connections)

        activities_cost.append(act_total)
        dining_cost.append(dine_total)
        transit_cost.append(trans_total)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Activities",
        x=day_labels,
        y=activities_cost,
        marker_color="#0284c7",
        hovertemplate="Day: %{x}<br>Activities: AED %{y:,.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Dining",
        x=day_labels,
        y=dining_cost,
        marker_color="#0d9488",
        hovertemplate="Day: %{x}<br>Dining: AED %{y:,.1f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Transit",
        x=day_labels,
        y=transit_cost,
        marker_color="#d97706",
        hovertemplate="Day: %{x}<br>Transit: AED %{y:,.1f}<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="stack",
        title=dict(
            text="<b>Daily Spend Progression (AED)</b>",
            font=dict(size=17, color="#0f172a", family="sans-serif"),
        ),
        xaxis=dict(
            tickfont=dict(color="#0f172a", size=13, family="sans-serif"),
            linecolor="#cbd5e1",
        ),
        yaxis=dict(
            title=dict(text="Spend (AED)", font=dict(color="#0f172a", size=13)),
            tickfont=dict(color="#334155", size=12),
            gridcolor="#e2e8f0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(color="#334155", size=13),
        ),
        margin=dict(l=20, r=20, t=50, b=50),
        height=340,
    )
    return fig


def render_alternatives_view(alternatives: List[AlternativeOption]):
    """Render budget-saving alternative recommendations."""
    if not alternatives:
        st.info("No alternative substitutions required. The itinerary matches budget constraints.")
        return

    st.subheader("💡 Budget Optimization Alternatives")
    st.caption("Lower-cost recommendations suggested to optimize overall spend.")

    for alt in alternatives:
        with st.container():
            col1, col2, col3 = st.columns([3, 3, 2])
            with col1:
                st.markdown(f"**Original:** {alt.original_item_name}")
            with col2:
                st.markdown(f"**Alternative:** {alt.replacement_item.name} (`AED {alt.replacement_item.cost_aed:.1f}`)")
                st.caption(f"Rationale: {alt.rationale}")
            with col3:
                st.success(f"Save AED {alt.savings_aed:,.1f}")
            st.divider()
