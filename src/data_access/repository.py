"""Unified repository facade uniting SQLite seed data, cache, and open APIs."""

from typing import List, Dict, Any, Optional
from src.data_access.sqlite_client import SQLiteClient
from src.data_access.cache import SimpleTTLCache
from src.data_access.osrm_client import OSRMClient
from src.data_access.open_meteo import OpenMeteoClient
from src.data_access.osm_client import OSMClient
from src.models.enums import DataSource
from src.models.itinerary import ActivityItem, TransitSegment
from configs.dubai_constants import DUBAI_ZONES, RTA_METRO_FARES, RTA_ABRA_CREEK_CROSSING


class DubaiDataRepository:
    """Unified data access facade implementing repository pattern with TTL caching."""

    _instance: Optional["DubaiDataRepository"] = None

    def __init__(self, db_path: Optional[str] = None):
        self.sqlite = SQLiteClient(db_path=db_path)
        self.cache = SimpleTTLCache(default_ttl_seconds=3600)
        self.osrm = OSRMClient()
        self.weather = OpenMeteoClient()
        self.osm = OSMClient()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "DubaiDataRepository":
        """Singleton accessor for repository facade."""
        if cls._instance is None:
            cls._instance = cls(db_path=db_path)
        return cls._instance

    # --- Attractions ---

    def search_attractions(
        self,
        category: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_price: Optional[float] = None,
        max_crowd: Optional[str] = None,
        is_indoor: Optional[bool] = None,
        limit: int = 20,
    ) -> List[ActivityItem]:
        """Search attractions matching criteria and return typed ActivityItem objects."""
        cache_key = f"attr:{category}:{neighborhood}:{max_price}:{max_crowd}:{is_indoor}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        raw_rows = self.sqlite.get_attractions(
            category=category,
            neighborhood=neighborhood,
            max_price=max_price,
            max_crowd=max_crowd,
            is_indoor=is_indoor,
            limit=limit,
        )

        items = []
        for r in raw_rows:
            # Map database category safely to Pydantic literal
            cat = r["category"]
            if cat not in ["culture", "beach", "dining", "sightseeing", "shopping", "adventure"]:
                cat = "sightseeing"

            items.append(
                ActivityItem(
                    name=r["name"],
                    category=cat,
                    neighborhood=r["neighborhood"],
                    lat=r["latitude"],
                    lng=r["longitude"],
                    duration_hours=r["typical_duration_hours"],
                    cost_aed=r["price_aed"],
                    cost_source=DataSource.SEED_DATABASE,
                    is_indoor=bool(r["is_indoor"]),
                    crowd_level=r["crowd_index"] or "medium",
                )
            )

        self.cache.set(cache_key, items)
        return items

    # --- Dining ---

    def search_dining(
        self,
        cuisine_type: Optional[str] = None,
        price_tier: Optional[str] = None,
        neighborhood: Optional[str] = None,
        authentic_only: bool = False,
        max_cost: Optional[float] = None,
        limit: int = 20,
    ) -> List[ActivityItem]:
        """Search restaurants matching criteria and return typed ActivityItem objects."""
        cache_key = f"dine:{cuisine_type}:{price_tier}:{neighborhood}:{authentic_only}:{max_cost}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        raw_rows = self.sqlite.get_dining(
            cuisine_type=cuisine_type,
            price_tier=price_tier,
            neighborhood=neighborhood,
            authentic_only=authentic_only,
            max_cost=max_cost,
            limit=limit,
        )

        items = []
        for r in raw_rows:
            items.append(
                ActivityItem(
                    name=r["name"],
                    category="dining",
                    neighborhood=r["neighborhood"],
                    lat=r["latitude"],
                    lng=r["longitude"],
                    duration_hours=1.5,
                    cost_aed=r["average_meal_cost_aed"],
                    cost_source=DataSource.SEED_DATABASE,
                    is_indoor=True,
                    crowd_level="medium",
                )
            )

        self.cache.set(cache_key, items)
        return items

    # --- Hotel Zones ---

    def get_hotel_zones(self) -> List[Dict[str, Any]]:
        """Return all hotel neighborhood zones."""
        cached = self.cache.get("hotel_zones")
        if cached is not None:
            return cached
        zones = self.sqlite.get_hotel_zones()
        self.cache.set("hotel_zones", zones, ttl_seconds=86400)
        return zones

    def get_hotel_zone(self, neighborhood: str) -> Optional[Dict[str, Any]]:
        """Return pricing for single hotel neighborhood."""
        return self.sqlite.get_hotel_zone(neighborhood)

    # --- Transit & Routing ---

    def calculate_transit_route(
        self,
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
        """Calculate transit connection using official RTA matrix or OSRM fallback."""
        cache_key = f"route:{origin_neighborhood}:{dest_neighborhood}:{preferred_mode}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Check for special abra crossing between Deira and Bur Dubai
        if (
            (origin_neighborhood == "Deira" and dest_neighborhood == "Bur Dubai")
            or (origin_neighborhood == "Bur Dubai" and dest_neighborhood == "Deira")
        ) and preferred_mode in ["abra", "walking"]:
            segment = TransitSegment(
                origin=origin_name,
                destination=dest_name,
                mode="abra",
                duration_minutes=10,
                fare_aed=RTA_ABRA_CREEK_CROSSING,
                fare_source=DataSource.RTA_OFFICIAL,
            )
            self.cache.set(cache_key, segment)
            return segment

        # Check local precomputed transit matrix in SQLite
        row = self.sqlite.get_transit_segment(origin_neighborhood, dest_neighborhood)
        if row:
            if preferred_mode == "taxi":
                segment = TransitSegment(
                    origin=origin_name,
                    destination=dest_name,
                    mode="taxi",
                    duration_minutes=row["taxi_time_min"],
                    fare_aed=row["taxi_est_aed"],
                    fare_source=DataSource.RTA_OFFICIAL,
                )
            else:
                segment = TransitSegment(
                    origin=origin_name,
                    destination=dest_name,
                    mode="metro",
                    duration_minutes=row["metro_time_min"],
                    fare_aed=row["metro_fare_aed"],
                    fare_source=DataSource.RTA_OFFICIAL,
                )
            self.cache.set(cache_key, segment)
            return segment

        # Fallback to dynamic OSRM / Haversine road calculation
        road_info = self.osrm.calculate_road_route(origin_lat, origin_lng, dest_lat, dest_lng)
        segment = TransitSegment(
            origin=origin_name,
            destination=dest_name,
            mode="taxi" if preferred_mode == "taxi" else "metro",
            duration_minutes=road_info["duration_minutes"],
            fare_aed=road_info["taxi_fare_aed"] if preferred_mode == "taxi" else 7.5,
            fare_source=road_info["source"],
        )
        self.cache.set(cache_key, segment)
        return segment

    # --- Weather ---

    def get_weather_forecast(self, days: int = 4) -> Dict[str, Any]:
        """Fetch weather forecast for Dubai."""
        cached = self.cache.get(f"weather:{days}")
        if cached is not None:
            return cached
        data = self.weather.get_forecast(days=days)
        self.cache.set(f"weather:{days}", data, ttl_seconds=14400)
        return data
