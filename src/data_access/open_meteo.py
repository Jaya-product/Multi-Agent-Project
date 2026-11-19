"""Free Open-Meteo weather forecast client with zero API keys."""

import requests
from typing import Dict, Any, List
from src.models.enums import DataSource


class OpenMeteoClient:
    """Client for unmetered open weather forecast data in Dubai."""

    DUBAI_LAT = 25.2048
    DUBAI_LNG = 55.2708

    def __init__(self, timeout_seconds: float = 3.0):
        self.timeout = timeout_seconds
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_forecast(self, days: int = 4) -> Dict[str, Any]:
        """Fetch daily max/min temperatures, precipitation, and UV index for Dubai."""
        params = {
            "latitude": self.DUBAI_LAT,
            "longitude": self.DUBAI_LNG,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,uv_index_max",
            "timezone": "auto",
            "forecast_days": min(days, 7),
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get("daily", {})
                return {
                    "source": DataSource.OPEN_METEO,
                    "dates": daily.get("time", []),
                    "temp_max": daily.get("temperature_2m_max", []),
                    "temp_min": daily.get("temperature_2m_min", []),
                    "precipitation_sum": daily.get("precipitation_sum", []),
                    "uv_max": daily.get("uv_index_max", []),
                    "is_outdoor_friendly": all(
                        temp < 38.0 for temp in daily.get("temperature_2m_max", [30.0])
                    ),
                }
        except Exception:
            pass  # Fall back to baseline Dubai weather

        # Baseline Dubai autumn/winter weather fallback
        return {
            "source": DataSource.SEED_DATABASE,
            "dates": [f"Day {i+1}" for i in range(days)],
            "temp_max": [31.0] * days,
            "temp_min": [23.0] * days,
            "precipitation_sum": [0.0] * days,
            "uv_max": [7.5] * days,
            "is_outdoor_friendly": True,
        }
