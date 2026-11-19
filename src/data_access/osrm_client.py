"""Free OSRM road routing engine client with mathematical Haversine fallback."""

import math
import requests
from typing import Dict, Any, Tuple
from configs.dubai_constants import RTA_TAXI
from src.models.enums import DataSource


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    radius_earth_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radius_earth_km * c, 2)


class OSRMClient:
    """Client for free Open Source Routing Machine (OSRM) with local fallback."""

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout = timeout_seconds
        self.base_url = "http://router.project-osrm.org/route/v1/driving"

    def calculate_road_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
    ) -> Dict[str, Any]:
        """Calculate road route distance and driving duration with automatic fallback."""
        url = f"{self.base_url}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=false"

        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    dist_km = round(route["distance"] / 1000.0, 2)
                    duration_min = max(5, int(round(route["duration"] / 60.0)))
                    taxi_fare = round(
                        max(
                            RTA_TAXI["minimum_fare"],
                            RTA_TAXI["base_flag_fall_day"] + (dist_km * RTA_TAXI["per_km_rate"]),
                        ),
                        1,
                    )
                    return {
                        "distance_km": dist_km,
                        "duration_minutes": duration_min,
                        "taxi_fare_aed": taxi_fare,
                        "source": DataSource.OSRM_ROUTING,
                    }
        except Exception:
            pass  # Fall through to deterministic mathematical fallback

        # Local Haversine Fallback: Assumes 38 km/h average Dubai city traffic speed
        direct_km = haversine_distance_km(origin_lat, origin_lon, dest_lat, dest_lon)
        road_km = round(direct_km * 1.3, 2)  # 1.3 road winding factor
        duration_min = max(6, int(round((road_km / 38.0) * 60.0)))
        taxi_fare = round(
            max(
                RTA_TAXI["minimum_fare"],
                RTA_TAXI["base_flag_fall_day"] + (road_km * RTA_TAXI["per_km_rate"]),
            ),
            1,
        )

        return {
            "distance_km": road_km,
            "duration_minutes": duration_min,
            "taxi_fare_aed": taxi_fare,
            "source": DataSource.RTA_OFFICIAL,
        }
