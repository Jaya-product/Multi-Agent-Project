"""Database initialization and seed ingestion script for Dubai AI Travel System."""

import json
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / "data" / "seed"
DB_DIR = BASE_DIR / "data" / "database"
DB_PATH = DB_DIR / "dubai_travel.db"


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create directory structure and initialize SQLite schema."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 1. Attractions Schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attractions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        neighborhood TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        price_aed REAL DEFAULT 0.0,
        typical_duration_hours REAL NOT NULL,
        crowd_index TEXT CHECK(crowd_index IN ('low', 'medium', 'high')),
        is_indoor BOOLEAN NOT NULL DEFAULT 0,
        opening_time TEXT,
        closing_time TEXT,
        description TEXT
    );
    """)

    # 2. Dining Schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dining (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cuisine_type TEXT NOT NULL,
        price_tier TEXT CHECK(price_tier IN ('budget', 'midscale', 'fine_dining')),
        neighborhood TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        average_meal_cost_aed REAL NOT NULL,
        is_authentic_local BOOLEAN DEFAULT 0
    );
    """)

    # 3. Hotel Zones Schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hotel_zones (
        zone_id TEXT PRIMARY KEY,
        neighborhood TEXT NOT NULL UNIQUE,
        avg_budget_rate_aed REAL NOT NULL,
        avg_midscale_rate_aed REAL NOT NULL,
        avg_luxury_rate_aed REAL NOT NULL,
        metro_accessible BOOLEAN NOT NULL,
        description TEXT
    );
    """)

    # 4. Transit Matrix Schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transit_matrix (
        origin_zone TEXT NOT NULL,
        destination_zone TEXT NOT NULL,
        metro_fare_aed REAL NOT NULL,
        metro_time_min INTEGER NOT NULL,
        taxi_est_aed REAL NOT NULL,
        taxi_time_min INTEGER NOT NULL,
        PRIMARY KEY (origin_zone, destination_zone)
    );
    """)

    # Fast lookup indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attr_cat_neigh ON attractions (category, neighborhood);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attr_price ON attractions (price_aed);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_dining_neigh_tier ON dining (neighborhood, price_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transit_origin ON transit_matrix (origin_zone);")

    conn.commit()
    return conn


def populate_seed_data(conn: sqlite3.Connection) -> None:
    """Populate database tables from curated JSON seed files."""
    cursor = conn.cursor()

    # Populate Attractions
    attractions_file = SEED_DIR / "attractions.json"
    if attractions_file.exists():
        with open(attractions_file, "r", encoding="utf-8") as f:
            attractions = json.load(f)
        for a in attractions:
            cursor.execute("""
            INSERT OR REPLACE INTO attractions 
            (id, name, category, neighborhood, latitude, longitude, price_aed, typical_duration_hours, crowd_index, is_indoor, opening_time, closing_time, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a["id"], a["name"], a["category"], a["neighborhood"],
                a["latitude"], a["longitude"], a["price_aed"], a["typical_duration_hours"],
                a["crowd_index"], int(a["is_indoor"]), a.get("opening_time"),
                a.get("closing_time"), a.get("description")
            ))

    # Populate Dining
    dining_file = SEED_DIR / "restaurants.json"
    if dining_file.exists():
        with open(dining_file, "r", encoding="utf-8") as f:
            dining = json.load(f)
        for d in dining:
            cursor.execute("""
            INSERT OR REPLACE INTO dining
            (id, name, cuisine_type, price_tier, neighborhood, latitude, longitude, average_meal_cost_aed, is_authentic_local)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                d["id"], d["name"], d["cuisine_type"], d["price_tier"],
                d["neighborhood"], d["latitude"], d["longitude"],
                d["average_meal_cost_aed"], int(d["is_authentic_local"])
            ))

    # Populate Hotel Zones
    hotel_file = SEED_DIR / "hotel_zones.json"
    if hotel_file.exists():
        with open(hotel_file, "r", encoding="utf-8") as f:
            zones = json.load(f)
        for z in zones:
            cursor.execute("""
            INSERT OR REPLACE INTO hotel_zones
            (zone_id, neighborhood, avg_budget_rate_aed, avg_midscale_rate_aed, avg_luxury_rate_aed, metro_accessible, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                z["zone_id"], z["neighborhood"], z["avg_budget_rate_aed"],
                z["avg_midscale_rate_aed"], z["avg_luxury_rate_aed"],
                int(z["metro_accessible"]), z.get("description")
            ))

    # Populate Transit Matrix
    transit_file = SEED_DIR / "transit_matrix.json"
    if transit_file.exists():
        with open(transit_file, "r", encoding="utf-8") as f:
            matrix = json.load(f)
        for t in matrix:
            cursor.execute("""
            INSERT OR REPLACE INTO transit_matrix
            (origin_zone, destination_zone, metro_fare_aed, metro_time_min, taxi_est_aed, taxi_time_min)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                t["origin_zone"], t["destination_zone"],
                t["metro_fare_aed"], t["metro_time_min"],
                t["taxi_est_aed"], t["taxi_time_min"]
            ))

    conn.commit()


def verify_db(conn: sqlite3.Connection) -> dict:
    """Return counts of inserted records across all tables."""
    cursor = conn.cursor()
    counts = {}
    for table in ["attractions", "dining", "hotel_zones", "transit_matrix"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def build_database_if_missing(db_path: Optional[Path] = None) -> bool:
    """Ensure database exists and is populated; if missing or empty, build and seed it automatically."""
    target_path = Path(db_path) if db_path is not None else DB_PATH
    if not target_path.exists() or target_path.stat().st_size == 0:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = init_db(target_path)
        populate_seed_data(conn)
        conn.close()
        return True
    return False


def main():
    print(f"Building SQLite database at: {DB_PATH}")
    conn = init_db()
    populate_seed_data(conn)
    counts = verify_db(conn)
    conn.close()
    print("Database built successfully!")
    for table, count in counts.items():
        print(f" - {table}: {count} records")


if __name__ == "__main__":
    main()
