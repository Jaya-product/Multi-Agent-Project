"""Attraction and dining discovery tools for agent execution."""

from typing import List, Optional
from src.data_access.repository import DubaiDataRepository
from src.models.itinerary import ActivityItem


def search_attractions(
    category: Optional[str] = None,
    neighborhood: Optional[str] = None,
    max_price: Optional[float] = None,
    max_crowd: Optional[str] = None,
    is_indoor: Optional[bool] = None,
    limit: int = 10,
) -> List[ActivityItem]:
    """Search attractions matching constraints from local curated Dubai database.
    
    Args:
        category: Filter by 'culture', 'beach', 'sightseeing', 'shopping', 'adventure'.
        neighborhood: Filter by 'Deira', 'Bur Dubai', 'Downtown', 'Jumeirah', 'Al Barsha', 'Dubai Marina', 'Palm Jumeirah'.
        max_price: Maximum admission price in AED.
        max_crowd: Maximum tolerable crowd level ('low', 'medium', 'high').
        is_indoor: Whether indoor venue is required.
        limit: Maximum results to return.
    """
    repo = DubaiDataRepository.get_instance()
    return repo.search_attractions(
        category=category,
        neighborhood=neighborhood,
        max_price=max_price,
        max_crowd=max_crowd,
        is_indoor=is_indoor,
        limit=limit,
    )


def search_restaurants(
    cuisine_type: Optional[str] = None,
    price_tier: Optional[str] = None,
    neighborhood: Optional[str] = None,
    authentic_only: bool = False,
    max_cost: Optional[float] = None,
    limit: int = 10,
) -> List[ActivityItem]:
    """Search restaurants matching cuisine, price tier, and neighborhood filters.
    
    Args:
        cuisine_type: E.g., 'Emirati', 'Middle Eastern', 'Levantine', 'Seafood', 'Pakistani'.
        price_tier: 'budget', 'midscale', or 'fine_dining'.
        neighborhood: Target Dubai neighborhood.
        authentic_only: If True, filters for authentic Emirati/Khaleeji eateries.
        max_cost: Maximum average meal cost in AED.
        limit: Maximum results to return.
    """
    repo = DubaiDataRepository.get_instance()
    return repo.search_dining(
        cuisine_type=cuisine_type,
        price_tier=price_tier,
        neighborhood=neighborhood,
        authentic_only=authentic_only,
        max_cost=max_cost,
        limit=limit,
    )
