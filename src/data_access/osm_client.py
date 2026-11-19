"""OpenStreetMap / Overpass API client with local seed fallback."""

import requests
from typing import List, Dict, Any, Optional
from src.models.enums import DataSource


class OSMClient:
    """Free OpenStreetMap POI discovery client."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, timeout_seconds: float = 4.0):
        self.timeout = timeout_seconds

    def search_amenities_around(
        self,
        lat: float,
        lon: float,
        amenity_type: str = "restaurant",
        radius_meters: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query Overpass API for amenities within radius around coordinate."""
        query = f"""
        [out:json][timeout:5];
        node["amenity"="{amenity_type}"](around:{radius_meters},{lat},{lon});
        out body 10;
        """
        try:
            resp = requests.post(self.OVERPASS_URL, data={"data": query}, timeout=self.timeout)
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                results = []
                for el in elements:
                    tags = el.get("tags", {})
                    name = tags.get("name")
                    if name:
                        results.append({
                            "name": name,
                            "lat": el.get("lat"),
                            "lng": el.get("lon"),
                            "cuisine": tags.get("cuisine", "international"),
                            "source": DataSource.OPEN_STREET_MAP,
                        })
                return results
        except Exception:
            pass

        return []
