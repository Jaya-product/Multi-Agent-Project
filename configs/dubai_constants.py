"""Official Dubai transit constants, fare matrices, and geographic zones."""

# RTA Public Transit Tariffs (AED)
RTA_METRO_FARES = {
    "tier_1_single_zone": {"silver": 3.0, "red": 4.0},
    "tier_2_two_zones": {"silver": 5.0, "red": 6.0},
    "tier_3_multi_zone": {"silver": 7.5, "red": 8.5},
    "gold_multiplier": 2.0,
    "red_ticket_issuance_fee": 2.0,
}

# RTA Taxi Tariffs (AED)
RTA_TAXI = {
    "base_flag_fall_day": 12.0,
    "base_flag_fall_night": 14.0,
    "per_km_rate": 2.09,
    "minimum_fare": 12.0,
    "salik_toll_gate": 4.0,
}

# Marine Transit & Monorail (AED)
RTA_ABRA_CREEK_CROSSING = 1.0  # Traditional Abra across Dubai Creek
PALM_MONORAIL_SINGLE = 10.0
PALM_MONORAIL_ROUNDTRIP = 15.0

# Geographic Neighborhood Clusters / Zones
DUBAI_ZONES = {
    "Deira": {
        "zone_code": "Zone_1",
        "region": "Old Dubai",
        "description": "Historic trading hub, traditional gold and spice souks, creek waterfront",
        "center_lat": 25.2697,
        "center_lng": 55.3095,
        "metro_accessible": True,
    },
    "Bur Dubai": {
        "zone_code": "Zone_2",
        "region": "Old Dubai",
        "description": "Heritage district, Al Fahidi Historical Neighbourhood, museums, textile souk",
        "center_lat": 25.2532,
        "center_lng": 55.2974,
        "metro_accessible": True,
    },
    "Downtown": {
        "zone_code": "Zone_3",
        "region": "New Dubai",
        "description": "Burj Khalifa, Dubai Mall, Dubai Opera, modern architecture & high-end dining",
        "center_lat": 25.1972,
        "center_lng": 55.2744,
        "metro_accessible": True,
    },
    "Jumeirah": {
        "zone_code": "Zone_4",
        "region": "Coastal",
        "description": "Public beaches, Kite Beach, upscale cafes, Jumeirah Mosque, Burj Al Arab views",
        "center_lat": 25.2048,
        "center_lng": 55.2415,
        "metro_accessible": False,  # Primary bus / taxi access
    },
    "Al Barsha": {
        "zone_code": "Zone_5",
        "region": "Central Hub",
        "description": "Affordable hotels, Mall of the Emirates, Ski Dubai, central transit hub",
        "center_lat": 25.1147,
        "center_lng": 55.2001,
        "metro_accessible": True,
    },
    "Dubai Marina": {
        "zone_code": "Zone_6",
        "region": "Coastal / Marina",
        "description": "Skyscraper waterfront, JBR The Beach, Dubai Marina Walk, luxury dining",
        "center_lat": 25.0805,
        "center_lng": 55.1403,
        "metro_accessible": True,  # Metro + Tram
    },
    "Palm Jumeirah": {
        "zone_code": "Zone_6_Palm",
        "region": "Island",
        "description": "Iconic artificial archipelago, Atlantis The Palm, The View at The Palm, Aquaventure",
        "center_lat": 25.1124,
        "center_lng": 55.1390,
        "metro_accessible": False,  # Connected by Monorail & Taxi
    },
}

# Constraint Rule Limits
DEFAULT_CONTINGENCY_BUFFER = 0.10  # 10% contingency on total budget
MAX_DAILY_ACTIVE_HOURS = 8.5      # Max daily itinerary hours (excluding rest)
MAX_TRANSIT_LEG_MINUTES = 45.0    # Soft limit for single transit segment in same half-day
MAX_REVIEW_ITERATIONS = 3         # Hard ceiling for self-correction feedback loop
MAX_TOKENS_PER_RUN = 50000        # Safeguard limit
