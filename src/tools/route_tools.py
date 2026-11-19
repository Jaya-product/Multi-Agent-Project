"""Transit, routing, and neighborhood zone evaluation tools."""

from typing import List, Dict, Any, Optional
from src.data_access.repository import DubaiDataRepository
from src.models.itinerary import TransitSegment


def calculate_transit_route(
    origin_name: str,
    dest_name: str,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    origin_neighborhood: str,
    dest_neighborhood: str,
    preferred_mode: str = "metro",
) -> TransitSegment:
    """Calculate point-to-point transit duration and fare using RTA fares and OSRM."""
    repo = DubaiDataRepository.get_instance()
    return repo.calculate_transit_route(
        origin_name=origin_name,
        dest_name=dest_name,
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        dest_lat=dest_lat,
        dest_lng=dest_lng,
        origin_neighborhood=origin_neighborhood,
        dest_neighborhood=dest_neighborhood,
        preferred_mode=preferred_mode,
    )


def get_neighborhood_zones(budget_tier: Optional[str] = "budget") -> List[Dict[str, Any]]:
    """Return all Dubai hotel zones filtered or ranked by average nightly rate."""
    repo = DubaiDataRepository.get_instance()
    zones = repo.get_hotel_zones()
    if budget_tier == "budget":
        return sorted(zones, key=lambda z: z["avg_budget_rate_aed"])
    elif budget_tier == "luxury":
        return sorted(zones, key=lambda z: z["avg_luxury_rate_aed"], reverse=True)
    return sorted(zones, key=lambda z: z["avg_midscale_rate_aed"])
