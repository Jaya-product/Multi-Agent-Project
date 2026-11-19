"""Interactive route map visualizer using Folium and PyDeck with Day filtering."""

from typing import List, Dict, Any, Optional
import streamlit as st
from src.models.itinerary import DailyPlan, ActivityItem


DAY_COLORS = [
    "#2563eb",  # Day 1: Royal Blue
    "#dc2626",  # Day 2: Crimson
    "#16a34a",  # Day 3: Emerald
    "#9333ea",  # Day 4: Violet
    "#ea580c",  # Day 5: Amber / Orange
    "#0891b2",  # Day 6: Cyan
    "#ca8a04",  # Day 7: Yellow / Gold
]


def render_route_map(days: List[DailyPlan], hotel_zone: Optional[Dict[str, Any]] = None):
    """Render interactive map showing day-by-day POIs and route polylines with UX filtering."""
    st.subheader("🗺️ Geographic Itinerary & Route Visualizer")
    st.markdown("<div style='font-size: 0.92rem; color: #475569; margin-bottom: 1rem;'>Visualizing spatial clustering, daily activity locations, and transit sequence across Dubai.</div>", unsafe_allow_html=True)

    if not days:
        st.info("No itinerary days available to display on map.")
        return

    # Interactive Day Filter Selector
    day_options = ["🌐 All Days Combined"] + [f"📍 Day {d.day_number}: {d.focus_area}" for d in days]
    selected_option = st.radio("Focus Map on Specific Day:", day_options, horizontal=True)

    if selected_option == "🌐 All Days Combined":
        active_days = days
    else:
        # Extract selected day number
        selected_day_num = int(selected_option.split("Day ")[1].split(":")[0])
        active_days = [d for d in days if d.day_number == selected_day_num]

    # Collect all points for active days
    all_points = []
    total_transit_legs = 0
    unique_neighborhoods = set()

    for day in active_days:
        day_color = DAY_COLORS[(day.day_number - 1) % len(DAY_COLORS)]
        slots = [
            ("Morning", day.morning_activity),
            ("Lunch", day.lunch_spot),
            ("Afternoon", day.afternoon_activity),
            ("Evening", day.evening_activity),
        ]
        total_transit_legs += len(day.transit_connections)
        for slot_name, item in slots:
            if item.lat and item.lng:
                unique_neighborhoods.add(item.neighborhood)
                all_points.append({
                    "day": day.day_number,
                    "slot": slot_name,
                    "name": item.name,
                    "category": item.category,
                    "neighborhood": item.neighborhood,
                    "lat": item.lat,
                    "lng": item.lng,
                    "cost": item.cost_aed,
                    "color": day_color,
                    "duration": item.duration_hours,
                })

    if not all_points:
        st.warning("No coordinates available to plot for the selected view.")
        return

    # Route Metric Strip
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    with mcol1:
        st.markdown(f"<div class='meta-chip' style='width:100%; justify-content:center; padding:8px;'>📍 <b>{len(all_points)}</b> Points of Interest</div>", unsafe_allow_html=True)
    with mcol2:
        st.markdown(f"<div class='meta-chip' style='width:100%; justify-content:center; padding:8px;'>🚗 <b>{total_transit_legs}</b> Transit Connections</div>", unsafe_allow_html=True)
    with mcol3:
        st.markdown(f"<div class='meta-chip' style='width:100%; justify-content:center; padding:8px;'>🏙️ <b>{len(unique_neighborhoods)}</b> Neighborhoods</div>", unsafe_allow_html=True)
    with mcol4:
        view_label = f"Day {active_days[0].day_number}" if len(active_days) == 1 else f"{len(days)} Days Active"
        st.markdown(f"<div class='meta-chip' style='width:100%; justify-content:center; padding:8px; background:#fffbeb; color:#92400e; border-color:#fde68a;'>🗺️ <b>{view_label}</b></div>", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Check for Folium availability
    try:
        import folium
        from streamlit_folium import st_folium

        # Center on average of active points
        avg_lat = sum(p["lat"] for p in all_points) / len(all_points)
        avg_lng = sum(p["lng"] for p in all_points) / len(all_points)
        zoom = 12 if len(active_days) == 1 else 11

        m = folium.Map(location=[avg_lat, avg_lng], zoom_start=zoom, tiles="CartoDB positron")

        # Plot points and connect daily polylines
        for day in active_days:
            day_idx = (day.day_number - 1) % len(DAY_COLORS)
            color = DAY_COLORS[day_idx]
            day_coords = []

            slots = [
                ("Morning", day.morning_activity),
                ("Lunch", day.lunch_spot),
                ("Afternoon", day.afternoon_activity),
                ("Evening", day.evening_activity),
            ]

            for slot_name, item in slots:
                if item.lat and item.lng:
                    day_coords.append((item.lat, item.lng))
                    popup_html = f"""
                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; line-height: 1.5; color: #0f172a; padding: 4px;">
                        <div style="color: {color}; font-weight: 800; font-size: 13px; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 3px; margin-bottom: 4px;">Day {day.day_number} — {slot_name}</div>
                        <b style="font-size: 14px; color: #0f172a;">{item.name}</b><br/>
                        <span style="color: #475569; font-size: 12px;">📍 {item.neighborhood} | 🏷️ {item.category.capitalize()}</span><br/>
                        <div style="margin-top: 5px; display: inline-flex; gap: 6px;">
                            <span style="background: #fef3c7; color: #92400e; font-weight: 700; padding: 2px 7px; border-radius: 4px; border: 1px solid #fde68a;">AED {item.cost_aed:,.1f}</span>
                            <span style="background: #f1f5f9; color: #334155; font-weight: 600; padding: 2px 7px; border-radius: 4px; border: 1px solid #e2e8f0;">⏱️ {item.duration_hours:.1f} hrs</span>
                        </div>
                    </div>
                    """
                    folium.CircleMarker(
                        location=[item.lat, item.lng],
                        radius=8,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.9,
                        popup=folium.Popup(popup_html, max_width=270),
                        tooltip=f"Day {day.day_number}: {item.name}",
                    ).add_to(m)

            # Draw route polyline between consecutive points of the day
            if len(day_coords) > 1:
                folium.PolyLine(
                    locations=day_coords,
                    color=color,
                    weight=3.5,
                    opacity=0.8,
                    dash_array="6",
                    tooltip=f"Day {day.day_number} Route Flow",
                ).add_to(m)

        # Legend / Filters in columns
        cols = st.columns(len(days))
        for idx, day in enumerate(days):
            day_c = DAY_COLORS[idx % len(DAY_COLORS)]
            with cols[idx]:
                st.markdown(
                    f"""
                    <div style="background: #ffffff; border: 1.5px solid #cbd5e1; border-top: 4px solid {day_c}; border-radius: 8px; padding: 0.55rem 0.75rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 0.85rem;">
                        <b style="color: {day_c}; font-size: 0.95rem;">Day {day.day_number}</b><br/>
                        <span style="font-size: 0.82rem; color: #334155; font-weight: 600;">{day.focus_area}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st_folium(m, width="100%", height=520, returned_objects=[])

    except Exception as e:
        # Graceful fallback to PyDeck / st.map
        st.info("Rendering map via PyDeck fallback.")
        import pandas as pd
        df = pd.DataFrame(all_points)
        st.map(df, latitude="lat", longitude="lng", size=15)
