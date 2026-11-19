"""SQLite query client for curated Dubai travel knowledge base."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from configs.settings import get_settings


class SQLiteClient:
    """Client for local SQLite database containing curated Dubai entities."""

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        target_path = db_path or settings.sqlite_db_path
        self.db_path = Path(target_path)
        if not self.db_path.is_absolute():
            # Resolve relative to project root
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = base_dir / target_path

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            try:
                from data.build_seed_db import build_database_if_missing
                build_database_if_missing(self.db_path)
            except Exception:
                pass

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database file not found at: {self.db_path}. "
                "Please run `python data/build_seed_db.py` to initialize it."
            )
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # --- Attractions Queries ---

    def get_attractions(
        self,
        category: Optional[str] = None,
        neighborhood: Optional[str] = None,
        max_price: Optional[float] = None,
        max_crowd: Optional[str] = None,
        is_indoor: Optional[bool] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query attractions matching optional filters."""
        query = "SELECT * FROM attractions WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category.lower())

        if neighborhood:
            query += " AND neighborhood = ?"
            params.append(neighborhood)

        if max_price is not None:
            query += " AND price_aed <= ?"
            params.append(max_price)

        if max_crowd:
            crowd_levels = {"low": ["low"], "medium": ["low", "medium"], "high": ["low", "medium", "high"]}
            allowed = crowd_levels.get(max_crowd.lower(), ["low", "medium", "high"])
            placeholders = ",".join("?" for _ in allowed)
            query += f" AND crowd_index IN ({placeholders})"
            params.extend(allowed)

        if is_indoor is not None:
            query += " AND is_indoor = ?"
            params.append(1 if is_indoor else 0)

        query += " ORDER BY price_aed ASC, name ASC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_attraction_by_id(self, attr_id: str) -> Optional[Dict[str, Any]]:
        """Lookup attraction by primary key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attractions WHERE id = ?", (attr_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_attraction_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Lookup attraction by exact or substring name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM attractions WHERE name LIKE ? LIMIT 1", (f"%{name}%",))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Dining Queries ---

    def get_dining(
        self,
        cuisine_type: Optional[str] = None,
        price_tier: Optional[str] = None,
        neighborhood: Optional[str] = None,
        authentic_only: bool = False,
        max_cost: Optional[float] = None,
        limit: int = 40,
    ) -> List[Dict[str, Any]]:
        """Query restaurants matching optional filters."""
        query = "SELECT * FROM dining WHERE 1=1"
        params: List[Any] = []

        if cuisine_type:
            query += " AND cuisine_type LIKE ?"
            params.append(f"%{cuisine_type}%")

        if price_tier:
            query += " AND price_tier = ?"
            params.append(price_tier.lower())

        if neighborhood:
            query += " AND neighborhood = ?"
            params.append(neighborhood)

        if authentic_only:
            query += " AND is_authentic_local = 1"

        if max_cost is not None:
            query += " AND average_meal_cost_aed <= ?"
            params.append(max_cost)

        query += " ORDER BY average_meal_cost_aed ASC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_dining_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Lookup restaurant by exact or substring name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dining WHERE name LIKE ? LIMIT 1", (f"%{name}%",))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Hotel Zones Queries ---

    def get_hotel_zones(self) -> List[Dict[str, Any]]:
        """Retrieve all hotel neighborhood zones."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hotel_zones ORDER BY avg_budget_rate_aed ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_hotel_zone(self, neighborhood: str) -> Optional[Dict[str, Any]]:
        """Retrieve hotel pricing for specific neighborhood."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hotel_zones WHERE neighborhood LIKE ? LIMIT 1", (f"%{neighborhood}%",))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Transit Matrix Queries ---

    def get_transit_segment(self, origin_zone: str, destination_zone: str) -> Optional[Dict[str, Any]]:
        """Retrieve precomputed transit duration and fares between two zones."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM transit_matrix 
                WHERE origin_zone = ? AND destination_zone = ?
                LIMIT 1
                """,
                (origin_zone, destination_zone),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
