"""Implementation of specialized LangGraph agent node functions."""

import os
import time
import re
from typing import Dict, Any, List, Optional
from configs.settings import get_settings
from configs.dubai_constants import DUBAI_ZONES, DEFAULT_CONTINGENCY_BUFFER
from src.graph.state import TravelPlanState
from src.models.request import UserTravelRequest
from src.models.itinerary import ActivityItem, DailyPlan, TransitSegment, FinalItineraryPlan
from src.models.budget import BudgetSummary, AlternativeOption
from src.models.review import ReviewResult
from src.models.enums import DataSource
from src.tools.search_tools import search_attractions, search_restaurants
from src.tools.route_tools import calculate_transit_route, get_neighborhood_zones
from src.tools.validation_engine import verify_constraints_rule_engine
from src.utils.logger import get_logger, log_node_trace
from src.utils.error_handler import safe_json_parse

logger = get_logger("graph_nodes")


# =====================================================================
# Node 1: parse_requirements_node
# =====================================================================

def parse_requirements_node(state: TravelPlanState) -> Dict[str, Any]:
    """Parse user's raw prompt into structured UserTravelRequest model."""
    start_time = time.perf_counter()
    raw_prompt = state.get("raw_prompt", "")
    logger.info(f"[parse_requirements_node] Parsing prompt: {raw_prompt[:60]}...")

    settings = get_settings()
    parsed_dict: Optional[Dict[str, Any]] = None

    # 1. Attempt LLM extraction if API key configured
    has_api_key = bool(
        settings.llm_api_key
        or settings.google_api_key
        or settings.groq_api_key
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )
    if has_api_key:
        try:
            from configs.llm_factory import get_llm
            from src.prompts.orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT, ORCHESTRATOR_USER_TEMPLATE
            llm = get_llm(settings)
            prompt = f"{ORCHESTRATOR_SYSTEM_PROMPT}\n\n{ORCHESTRATOR_USER_TEMPLATE.format(user_prompt=raw_prompt)}"
            response = llm.invoke(prompt)
            parsed_dict = safe_json_parse(response.content)
        except Exception as e:
            logger.warning(f"[parse_requirements_node] LLM extraction failed ({e}), falling back to deterministic parser")

    # 2. Deterministic Regex / Keyword Fallback Parser
    if not parsed_dict:
        # Extract days (e.g. "3 days", "3-day", "3d")
        days = 4
        day_match = re.search(r"(\d+)\s*[-/]?\s*(?:days?|d\b)", raw_prompt, re.IGNORECASE)
        if day_match:
            days = max(1, min(7, int(day_match.group(1))))

        # Extract budget in AED
        budget = 5000.0
        budget_match = re.search(r"(?:(?:aed|dhs?|dirhams?|\$)\s*(\d[\d,]*))|(?:(\d[\d,]*)\s*(?:aed|dhs?|dirhams?|\$))", raw_prompt, re.IGNORECASE)
        if budget_match:
            raw_val = budget_match.group(1) or budget_match.group(2)
            if raw_val:
                cleaned = raw_val.replace(",", "").strip()
                if cleaned:
                    val = float(cleaned)
                    if "$" in raw_prompt:
                        val *= 3.67
                    budget = max(500.0, val)
        else:
            # Fallback bare number heuristic
            num_match = re.search(r"budget\s*(?:of|is|:)?\s*(\d[\d,]*)", raw_prompt, re.IGNORECASE)
            if num_match:
                cleaned = num_match.group(1).replace(",", "").strip()
                if cleaned:
                    budget = float(cleaned)

        # Extract interests
        interests = []
        prompt_lower = raw_prompt.lower()
        if any(w in prompt_lower for w in ["cultur", "heritage", "history", "museum", "old dubai", "souk"]):
            interests.append("culture")
        if any(w in prompt_lower for w in ["beach", "sea", "coastal", "ocean", "relax"]):
            interests.append("beach")
        if any(w in prompt_lower for w in ["food", "dining", "cuisine", "eat", "restaurant", "culinary"]):
            interests.append("dining")
        if any(w in prompt_lower for w in ["shop", "mall", "market"]):
            interests.append("shopping")
        if any(w in prompt_lower for w in ["adventure", "theme park", "thrill", "safari"]):
            interests.append("adventure")
        if not interests or any(w in prompt_lower for w in ["sight", "view", "tower", "burj"]):
            interests.append("sightseeing")

        # Hotel tier
        hotel_tier = "budget"
        if any(w in prompt_lower for w in ["luxury", "5 star", "upscale", "resort"]):
            hotel_tier = "luxury"
        elif any(w in prompt_lower for w in ["midscale", "4 star", "boutique", "moderate"]):
            hotel_tier = "midscale"

        # Pace
        pace = "moderate"
        if any(w in prompt_lower for w in ["relaxed", "slow", "easy"]):
            pace = "relaxed"
        elif any(w in prompt_lower for w in ["fast", "packed", "action"]):
            pace = "fast-paced"

        parsed_dict = {
            "raw_prompt": raw_prompt,
            "duration_days": days,
            "budget_aed": budget,
            "interests": interests,
            "hotel_tier": hotel_tier,
            "pace": pace,
            "avoid_crowds": ("crowd" not in prompt_lower or "avoid" in prompt_lower),
        }

    user_req = UserTravelRequest(**parsed_dict)
    elapsed = time.perf_counter() - start_time
    trace = log_node_trace("parse_requirements_node", elapsed, details={"days": user_req.duration_days, "budget": user_req.budget_aed})

    return {
        "user_request": user_req,
        "node_traces": [trace],
    }


# =====================================================================
# Node 2: destination_research_node
# =====================================================================

def destination_research_node(state: TravelPlanState) -> Dict[str, Any]:
    """Research and select candidate attractions and dining venues."""
    start_time = time.perf_counter()
    user_req = state.get("user_request")
    if not user_req:
        user_req = UserTravelRequest(raw_prompt=state.get("raw_prompt", ""))

    logger.info(f"[destination_research_node] Researching candidates for {user_req.duration_days} days...")
    revision_note = state.get("revision_instructions")

    # Determine needed candidate volume (approx 2 attractions + 2 dining spots per day)
    needed_attractions = user_req.duration_days * 2
    needed_dining = user_req.duration_days * 2

    # Query local database for attractions matching user interests
    matched_attractions: List[ActivityItem] = []
    for interest in user_req.interests:
        pois = search_attractions(
            category=interest,
            max_crowd="medium" if user_req.avoid_crowds else "high",
            limit=4,
        )
        matched_attractions.extend(pois)

    # Supplement with top sightseeing venues if needed
    if len(matched_attractions) < needed_attractions:
        supplemental = search_attractions(category="sightseeing", limit=needed_attractions - len(matched_attractions) + 2)
        matched_attractions.extend(supplemental)

    # Deduplicate candidate attractions while preserving order
    unique_attractions: List[ActivityItem] = []
    seen_attr = set()
    for a in matched_attractions:
        if a.name not in seen_attr:
            seen_attr.add(a.name)
            unique_attractions.append(a)

    # Query dining venues matching tier
    matched_dining = search_restaurants(
        price_tier=user_req.hotel_tier if user_req.hotel_tier in ["budget", "midscale"] else "midscale",
        limit=needed_dining + 4,
    )
    unique_dining: List[ActivityItem] = []
    seen_dine = set()
    for d in matched_dining:
        if d.name not in seen_dine:
            seen_dine.add(d.name)
            unique_dining.append(d)

    # If this is a revision addressing preference omission, ensure priority
    if revision_note and "PREFERENCE_OMISSION" in revision_note:
        if "culture" in revision_note.lower():
            unique_attractions = search_attractions(category="culture", limit=4) + unique_attractions
        if "beach" in revision_note.lower():
            unique_attractions = search_attractions(category="beach", limit=3) + unique_attractions

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "destination_research_node",
        elapsed,
        details={
            "attractions_found": len(unique_attractions),
            "dining_found": len(unique_dining),
        },
    )

    return {
        "candidate_attractions": unique_attractions[:needed_attractions + 2],
        "candidate_dining": unique_dining[:needed_dining + 2],
        "node_traces": [trace],
    }


# =====================================================================
# Node 3: logistics_routing_node
# =====================================================================

def logistics_routing_node(state: TravelPlanState) -> Dict[str, Any]:
    """Sequence activities geographically and calculate transit connections."""
    start_time = time.perf_counter()
    user_req = state.get("user_request")
    if not user_req:
        user_req = UserTravelRequest(raw_prompt=state.get("raw_prompt", ""))

    logger.info(f"[logistics_routing_node] Building transit and daily schedules...")

    # 1. Select optimal hotel zone
    zones = get_neighborhood_zones(budget_tier=user_req.hotel_tier)
    # Default selection based on interest and tier
    if "culture" in user_req.interests and user_req.hotel_tier == "budget":
        selected_zone = next((z for z in zones if z["neighborhood"] == "Bur Dubai"), zones[0])
    elif user_req.hotel_tier == "luxury":
        selected_zone = next((z for z in zones if z["neighborhood"] == "Downtown"), zones[0])
    else:
        selected_zone = zones[0]

    nightly_rate = selected_zone[f"avg_{user_req.hotel_tier}_rate_aed"]
    hotel_info = {
        "neighborhood": selected_zone["neighborhood"],
        "nightly_rate_aed": nightly_rate,
        "total_hotel_cost_aed": nightly_rate * user_req.duration_days,
        "metro_accessible": bool(selected_zone["metro_accessible"]),
    }

    # 2. Pool available activities and ensure uniqueness
    raw_attractions = list(state.get("candidate_attractions", []))
    raw_dining = list(state.get("candidate_dining", []))

    # Deduplicate candidate attractions by name
    candidate_attractions: List[ActivityItem] = []
    seen_attr = set()
    for a in raw_attractions:
        if a.name not in seen_attr:
            seen_attr.add(a.name)
            candidate_attractions.append(a)

    # If pool is insufficient for trip duration, supplement from database with unseen venues
    needed_attractions = user_req.duration_days * 2
    if len(candidate_attractions) < needed_attractions:
        all_db_attractions = search_attractions(limit=50)
        for a in all_db_attractions:
            if a.name not in seen_attr:
                seen_attr.add(a.name)
                candidate_attractions.append(a)
                if len(candidate_attractions) >= needed_attractions:
                    break

    # Deduplicate candidate dining by name
    candidate_dining: List[ActivityItem] = []
    seen_dine = set()
    for d in raw_dining:
        if d.name not in seen_dine:
            seen_dine.add(d.name)
            candidate_dining.append(d)

    # Supplement dining from database with unseen venues
    needed_dining = user_req.duration_days * 2
    if len(candidate_dining) < needed_dining:
        all_db_dining = search_restaurants(limit=50)
        for d in all_db_dining:
            if d.name not in seen_dine:
                seen_dine.add(d.name)
                candidate_dining.append(d)
                if len(candidate_dining) >= needed_dining:
                    break

    # 3. Assemble Daily Plans
    daily_schedules: List[DailyPlan] = []
    attr_idx = 0
    dine_idx = 0

    for day_i in range(1, user_req.duration_days + 1):
        morning = candidate_attractions[attr_idx % len(candidate_attractions)]
        attr_idx += 1
        lunch = candidate_dining[dine_idx % len(candidate_dining)]
        dine_idx += 1
        afternoon = candidate_attractions[attr_idx % len(candidate_attractions)]
        attr_idx += 1
        evening = candidate_dining[dine_idx % len(candidate_dining)]
        dine_idx += 1

        # Calculate transit segments between items
        t1 = calculate_transit_route(
            origin_name=morning.name,
            dest_name=lunch.name,
            origin_lat=morning.lat,
            origin_lng=morning.lng,
            dest_lat=lunch.lat,
            dest_lng=lunch.lng,
            origin_neighborhood=morning.neighborhood,
            dest_neighborhood=lunch.neighborhood,
            preferred_mode="metro",
        )
        t2 = calculate_transit_route(
            origin_name=lunch.name,
            dest_name=afternoon.name,
            origin_lat=lunch.lat,
            origin_lng=lunch.lng,
            dest_lat=afternoon.lat,
            dest_lng=afternoon.lng,
            origin_neighborhood=lunch.neighborhood,
            dest_neighborhood=afternoon.neighborhood,
            preferred_mode="metro",
        )
        t3 = calculate_transit_route(
            origin_name=afternoon.name,
            dest_name=evening.name,
            origin_lat=afternoon.lat,
            origin_lng=afternoon.lng,
            dest_lat=evening.lat,
            dest_lng=evening.lng,
            origin_neighborhood=afternoon.neighborhood,
            dest_neighborhood=evening.neighborhood,
            preferred_mode="metro",
        )

        connections = [t1, t2, t3]
        transit_cost = sum(c.fare_aed for c in connections)
        day_cost = morning.cost_aed + lunch.cost_aed + afternoon.cost_aed + evening.cost_aed + transit_cost

        daily_schedules.append(
            DailyPlan(
                day_number=day_i,
                focus_area=f"{morning.neighborhood} & Surrounds",
                morning_activity=morning,
                lunch_spot=lunch,
                afternoon_activity=afternoon,
                evening_activity=evening,
                transit_connections=connections,
                day_cost_aed=round(day_cost, 2),
            )
        )

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "logistics_routing_node",
        elapsed,
        details={
            "hotel_zone": hotel_info["neighborhood"],
            "days_scheduled": len(daily_schedules),
        },
    )

    return {
        "selected_hotel_zone": hotel_info,
        "daily_schedules": daily_schedules,
        "node_traces": [trace],
    }


# =====================================================================
# Node 4: budget_calculator_node
# =====================================================================

def budget_calculator_node(state: TravelPlanState) -> Dict[str, Any]:
    """Aggregate total trip costs and generate cost-saving alternatives."""
    start_time = time.perf_counter()
    user_req = state.get("user_request")
    if not user_req:
        user_req = UserTravelRequest(raw_prompt=state.get("raw_prompt", ""))

    daily_schedules = state.get("daily_schedules", [])
    hotel_info = state.get("selected_hotel_zone", {})

    logger.info(f"[budget_calculator_node] Calculating budget for {len(daily_schedules)} days...")

    accommodation_cost = float(hotel_info.get("total_hotel_cost_aed", 0.0))
    activities_cost = 0.0
    dining_cost = 0.0
    transport_cost = 0.0

    for day in daily_schedules:
        if day.morning_activity:
            activities_cost += day.morning_activity.cost_aed
        if day.afternoon_activity:
            activities_cost += day.afternoon_activity.cost_aed
        if day.lunch_spot:
            dining_cost += day.lunch_spot.cost_aed
        if day.evening_activity:
            dining_cost += day.evening_activity.cost_aed
        for seg in day.transit_connections:
            transport_cost += seg.fare_aed

    subtotal = accommodation_cost + activities_cost + dining_cost + transport_cost
    total_with_buffer = round(subtotal * (1.0 + DEFAULT_CONTINGENCY_BUFFER), 2)
    budget_limit = user_req.budget_aed
    is_compliant = total_with_buffer <= budget_limit
    variance = round(budget_limit - total_with_buffer, 2)

    summary = BudgetSummary(
        accommodation_cost=round(accommodation_cost, 2),
        activities_cost=round(activities_cost, 2),
        dining_cost=round(dining_cost, 2),
        transport_cost=round(transport_cost, 2),
        total_cost=round(subtotal, 2),
        budget_limit=budget_limit,
        is_compliant=is_compliant,
        variance_aed=variance,
    )

    # If exceeding budget or tight, propose lower-cost alternative options
    alternatives: List[AlternativeOption] = []
    if not is_compliant:
        for day in daily_schedules:
            for act in [day.morning_activity, day.afternoon_activity]:
                if act and act.cost_aed > 100.0:
                    cheaper_pois = search_attractions(category=act.category, max_price=50.0, limit=2)
                    if cheaper_pois and cheaper_pois[0].name != act.name:
                        repl = cheaper_pois[0]
                        alternatives.append(
                            AlternativeOption(
                                original_item_name=act.name,
                                replacement_item=repl,
                                savings_aed=round(act.cost_aed - repl.cost_aed, 2),
                                rationale=f"Substitute high-cost venue {act.name} (AED {act.cost_aed}) with {repl.name} (AED {repl.cost_aed}) for instant savings.",
                            )
                        )

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "budget_calculator_node",
        elapsed,
        details={
            "total_spend_aed": subtotal,
            "is_compliant": is_compliant,
            "alternatives_count": len(alternatives),
        },
    )

    return {
        "budget_summary": summary,
        "alternative_options": alternatives,
        "node_traces": [trace],
    }


# =====================================================================
# Node 5: review_validator_node
# =====================================================================

def review_validator_node(state: TravelPlanState) -> Dict[str, Any]:
    """Execute deterministic 5-rule check and qualitative evaluation."""
    start_time = time.perf_counter()
    user_req = state.get("user_request")
    if not user_req:
        user_req = UserTravelRequest(raw_prompt=state.get("raw_prompt", ""))

    daily_schedules = state.get("daily_schedules", [])
    budget_summary = state.get("budget_summary")

    if not budget_summary:
        budget_summary = BudgetSummary(
            accommodation_cost=0.0,
            activities_cost=0.0,
            dining_cost=0.0,
            transport_cost=0.0,
            total_cost=0.0,
            budget_limit=user_req.budget_aed,
            is_compliant=True,
        )

    logger.info(f"[review_validator_node] Auditing constraints for iteration {state.get('revision_count', 0) + 1}...")

    # Run deterministic validation engine
    result = verify_constraints_rule_engine(
        days=daily_schedules,
        budget_summary=budget_summary,
        user_request=user_req,
    )
    result.iteration = state.get("revision_count", 0) + 1

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "review_validator_node",
        elapsed,
        status="PASSED" if result.approved else "FAILED",
        details={
            "approved": result.approved,
            "violations_count": len(result.violations),
            "iteration": result.iteration,
        },
    )

    return {
        "review_result": result,
        "node_traces": [trace],
    }


# =====================================================================
# Node 6: revision_dispatcher_node
# =====================================================================

def revision_dispatcher_node(state: TravelPlanState) -> Dict[str, Any]:
    """Process review violations and dispatch corrective instructions to state."""
    start_time = time.perf_counter()
    review = state.get("review_result")
    current_count = state.get("revision_count", 0) + 1

    violations = review.violations if review else []
    logger.info(f"[revision_dispatcher_node] Dispatching revision #{current_count} for violations: {violations}")

    # Prioritize instructions: Budget > Pacing > Transit > Preference
    feedback_notes: List[str] = []
    for v in violations:
        if "OVER_BUDGET" in v:
            feedback_notes.append("BUDGET: Swap high-cost activities with free heritage sites/beaches or choose budget dining.")
        elif "PACE_EXCEEDED" in v:
            feedback_notes.append("PACING: Reduce activity durations so total active daily hours remain <= 8.5h.")
        elif "EXCESSIVE_TRANSIT" in v:
            feedback_notes.append("TRANSIT: Re-cluster activities into adjacent neighborhoods to ensure travel time < 45m.")
        elif "PREFERENCE_OMISSION" in v:
            feedback_notes.append(f"PREFERENCE: {v}")
        elif "DUPLICATE_ACTIVITY" in v:
            feedback_notes.append("DEDUPLICATION: Replace repeated venue with unique POI.")

    consolidated_instructions = "; ".join(feedback_notes) if feedback_notes else "Resolve itinerary violations."

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "revision_dispatcher_node",
        elapsed,
        details={
            "revision_count": current_count,
            "instructions": consolidated_instructions,
        },
    )

    return {
        "revision_count": current_count,
        "revision_instructions": consolidated_instructions,
        "node_traces": [trace],
    }


# =====================================================================
# Node 7: synthesize_final_plan_node
# =====================================================================

def synthesize_final_plan_node(state: TravelPlanState) -> Dict[str, Any]:
    """Assemble final validated deliverable for presentation and UI rendering."""
    start_time = time.perf_counter()
    user_req = state.get("user_request")
    if not user_req:
        user_req = UserTravelRequest(raw_prompt=state.get("raw_prompt", ""))

    daily_schedules = state.get("daily_schedules", [])
    budget_summary = state.get("budget_summary")
    alternatives = state.get("alternative_options", [])
    review = state.get("review_result") or ReviewResult(approved=True, iteration=1)

    logger.info(f"[synthesize_final_plan_node] Compiling final {len(daily_schedules)}-day itinerary deliverable...")

    interests_str = ", ".join(i.capitalize() for i in user_req.interests)
    title = f"{user_req.duration_days}-Day Dubai Itinerary ({interests_str})"

    # Calculate total execution time from node traces
    traces = state.get("node_traces", [])
    total_time = sum(t.get("latency_seconds", 0.0) for t in traces)
    elapsed_total = total_time if total_time > 0 else (time.perf_counter() - start_time)
    exec_time = max(0.01, round(elapsed_total, 3))

    final_plan = FinalItineraryPlan(
        trip_title=title,
        thread_id="travel_thread_default",
        user_profile=user_req,
        days=daily_schedules,
        budget_breakdown=budget_summary,
        alternatives=alternatives,
        review_summary=review,
        execution_time_seconds=exec_time,
    )

    elapsed = time.perf_counter() - start_time
    trace = log_node_trace(
        "synthesize_final_plan_node",
        elapsed,
        details={"trip_title": title, "days": len(daily_schedules)},
    )

    return {
        "final_plan": final_plan,
        "node_traces": [trace],
    }
