"""Enumerations for provenance tracking and categorical types."""

from enum import Enum


class DataSource(str, Enum):
    """Explicit data provenance source tag for every cost estimate and activity."""

    SEED_DATABASE = "seed_database"        # Pre-verified curated local SQLite data
    OPEN_METEO = "open_meteo"              # Free Open-Meteo weather forecast
    RTA_OFFICIAL = "rta_official"          # Official Dubai RTA fare tables in SQLite
    OPEN_STREET_MAP = "open_street_map"    # Free OpenStreetMap / Overpass API
    OSRM_ROUTING = "osrm_routing"          # Free OSRM road routing engine
    LLM_ESTIMATE = "llm_estimate"          # LLM approximation (transparently tagged)
