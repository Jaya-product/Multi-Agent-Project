"""Runtime configuration management using Pydantic Settings."""

import os
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def _sync_streamlit_secrets():
    """Synchronize Streamlit Cloud or secrets.toml into os.environ if running inside Streamlit."""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for k, v in st.secrets.items():
                if isinstance(v, (str, int, float, bool)) and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        pass


_sync_streamlit_secrets()


class AppSettings(BaseSettings):
    """Central configuration parameters for Dubai Travel Planning System."""

    model_config = SettingsConfigDict(
        env_file=(".env", "key.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- LLM Provider Configuration ---
    llm_provider: Literal["google", "groq", "openai", "anthropic", "ollama"] = "google"
    llm_model_name: str = "gemini-2.5-flash"
    llm_api_key: Optional[str] = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096

    # Dedicated Provider API Keys
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # --- Fallback LLM (optional) ---
    fallback_llm_provider: Optional[str] = None
    fallback_llm_model: Optional[str] = None
    fallback_llm_api_key: Optional[str] = None

    # --- Feature Flags (100% Free Stack) ---
    enable_weather_integration: bool = True       # Open-Meteo (zero-key, free)
    enable_osrm_routing: bool = True              # OSRM road routing (free)
    enable_human_in_the_loop: bool = False        # Pauses graph for user review

    # --- Execution Limits & Storage ---
    max_review_iterations: int = 3
    max_tokens_per_run: int = 50000
    api_cache_ttl_hours: int = 168               # 7-day cache TTL
    sqlite_db_path: str = "data/database/dubai_travel.db"


def get_settings() -> AppSettings:
    """Return cached singleton instance of AppSettings."""
    return AppSettings()
