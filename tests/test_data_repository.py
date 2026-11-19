"""Unit tests for SQLite client, cache, and DubaiDataRepository."""

import pytest
from src.data_access.repository import DubaiDataRepository
from src.data_access.cache import SimpleTTLCache
from src.data_access.osrm_client import haversine_distance_km
from src.models.enums import DataSource


def test_cache_ttl_and_expiry():
    cache = SimpleTTLCache(default_ttl_seconds=1)
    cache.set("key1", "value1", ttl_seconds=10)
    assert cache.get("key1") == "value1"
    assert cache.has("key1") is True

    # Immediate expiration test
    cache.set("short_key", "temp", ttl_seconds=-1)
    assert cache.get("short_key") is None
    assert cache.has("short_key") is False


def test_haversine_distance():
    # Distance between Downtown Dubai (Burj Khalifa) and Dubai Marina
    # (~18 to 22 km)
    dist = haversine_distance_km(25.1972, 55.2744, 25.0805, 55.1403)
    assert 17.0 <= dist <= 23.0


def test_repository_search_attractions():
    repo = DubaiDataRepository.get_instance()
    culture_pois = repo.search_attractions(category="culture", limit=5)
    assert len(culture_pois) > 0
    assert all(p.category == "culture" for p in culture_pois)
    assert all(p.cost_source == DataSource.SEED_DATABASE for p in culture_pois)


def test_repository_search_dining():
    repo = DubaiDataRepository.get_instance()
    budget_eats = repo.search_dining(price_tier="budget", limit=5)
    assert len(budget_eats) > 0
    assert all(d.cost_aed <= 60.0 for d in budget_eats)


def test_repository_hotel_zones():
    repo = DubaiDataRepository.get_instance()
    zones = repo.get_hotel_zones()
    assert len(zones) >= 6
    zone_names = [z["neighborhood"] for z in zones]
    assert "Deira" in zone_names
    assert "Downtown" in zone_names
    assert "Dubai Marina" in zone_names


def test_repository_transit_calculation():
    repo = DubaiDataRepository.get_instance()
    # Test Deira to Bur Dubai abra connection
    abra_segment = repo.calculate_transit_route(
        origin_name="Gold Souk",
        dest_name="Dubai Museum",
        origin_lat=25.2711,
        origin_lng=55.2988,
        dest_lat=25.2631,
        dest_lng=55.2974,
        origin_neighborhood="Deira",
        dest_neighborhood="Bur Dubai",
        preferred_mode="abra",
    )
    assert abra_segment.mode == "abra"
    assert abra_segment.fare_aed == 1.0

    # Test Metro route from Deira to Dubai Marina
    metro_segment = repo.calculate_transit_route(
        origin_name="Deira City Center",
        dest_name="Marina Walk",
        origin_lat=25.2697,
        origin_lng=55.3095,
        dest_lat=25.0805,
        dest_lng=55.1403,
        origin_neighborhood="Deira",
        dest_neighborhood="Dubai Marina",
        preferred_mode="metro",
    )
    assert metro_segment.mode == "metro"
    assert metro_segment.fare_aed == 7.5
    assert metro_segment.duration_minutes >= 30
