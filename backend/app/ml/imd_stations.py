"""
IMD Station Ground-Truth Reference Data.

In production this would be fetched from IMD API / satellite grid.
For demo: a hand-curated table of real IMD AWS stations with known
typical weather patterns per season, covering all Indian met divisions.

Each station entry:
  id, name, lat, lon, state, typical_events[]
"""
from typing import Optional
import math

IMD_STATIONS = [
    # --- North India ---
    {"id": "DEL01", "name": "Safdarjung (Delhi)", "lat": 28.5875, "lon": 77.0500, "state": "Delhi",
     "events": ["fog", "heatwave", "thunderstorm", "rain", "dust_storm"]},
    {"id": "DEL02", "name": "Palam (Delhi)", "lat": 28.5562, "lon": 77.1000, "state": "Delhi",
     "events": ["fog", "heatwave", "rain"]},
    {"id": "LKO01", "name": "Amausi (Lucknow)", "lat": 26.7606, "lon": 80.8893, "state": "Uttar Pradesh",
     "events": ["fog", "rain", "flood", "heatwave"]},
    {"id": "CHD01", "name": "Chandigarh AWS", "lat": 30.6736, "lon": 76.7885, "state": "Chandigarh",
     "events": ["rain", "fog", "thunderstorm", "hailstorm"]},
    {"id": "SML01", "name": "Shimla", "lat": 31.1048, "lon": 77.1734, "state": "Himachal Pradesh",
     "events": ["rain", "snow", "hailstorm", "thunderstorm"]},
    {"id": "JMU01", "name": "Jammu", "lat": 32.7266, "lon": 74.8570, "state": "J&K",
     "events": ["rain", "thunderstorm", "fog"]},
    {"id": "AMR01", "name": "Amritsar", "lat": 31.6340, "lon": 74.8723, "state": "Punjab",
     "events": ["fog", "heatwave", "rain", "thunderstorm"]},
    {"id": "JDH01", "name": "Jodhpur", "lat": 26.3011, "lon": 73.0243, "state": "Rajasthan",
     "events": ["heatwave", "drought", "dust_storm", "rain"]},
    {"id": "JAI01", "name": "Jaipur", "lat": 26.8241, "lon": 75.8022, "state": "Rajasthan",
     "events": ["heatwave", "rain", "thunderstorm", "drought"]},
    # --- West India ---
    {"id": "MUM01", "name": "Santacruz (Mumbai)", "lat": 19.0760, "lon": 72.8777, "state": "Maharashtra",
     "events": ["rain", "flood", "cyclone", "thunderstorm"]},
    {"id": "MUM02", "name": "Colaba (Mumbai)", "lat": 18.9067, "lon": 72.8147, "state": "Maharashtra",
     "events": ["rain", "cyclone", "thunderstorm"]},
    {"id": "PUN01", "name": "Pune", "lat": 18.5204, "lon": 73.8567, "state": "Maharashtra",
     "events": ["rain", "heatwave", "thunderstorm"]},
    {"id": "NGL01", "name": "Nagpur", "lat": 21.1458, "lon": 79.0882, "state": "Maharashtra",
     "events": ["heatwave", "rain", "thunderstorm"]},
    {"id": "AMD01", "name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "state": "Gujarat",
     "events": ["heatwave", "cyclone", "rain", "drought"]},
    {"id": "BHJ01", "name": "Bhuj (Kutch)", "lat": 23.2521, "lon": 69.6689, "state": "Gujarat",
     "events": ["cyclone", "drought", "heatwave", "rain", "dust_storm"]},
    {"id": "KND01", "name": "Kandla", "lat": 23.0300, "lon": 70.2167, "state": "Gujarat",
     "events": ["cyclone", "rain", "heatwave"]},
    {"id": "SUR01", "name": "Surat", "lat": 21.1702, "lon": 72.8311, "state": "Gujarat",
     "events": ["rain", "cyclone", "flood"]},
    # --- South India ---
    {"id": "CHE01", "name": "Nungambakkam (Chennai)", "lat": 13.0827, "lon": 80.2707, "state": "Tamil Nadu",
     "events": ["rain", "cyclone", "flood", "thunderstorm"]},
    {"id": "CHE02", "name": "Meenambakkam (Chennai)", "lat": 12.9941, "lon": 80.1709, "state": "Tamil Nadu",
     "events": ["rain", "cyclone", "thunderstorm"]},
    {"id": "BLR01", "name": "HAL (Bengaluru)", "lat": 12.9716, "lon": 77.5946, "state": "Karnataka",
     "events": ["rain", "thunderstorm", "hailstorm"]},
    {"id": "HYD01", "name": "Begumpet (Hyderabad)", "lat": 17.4065, "lon": 78.4772, "state": "Telangana",
     "events": ["rain", "flood", "thunderstorm", "heatwave"]},
    {"id": "COC01", "name": "Cochin", "lat": 9.9312, "lon": 76.2673, "state": "Kerala",
     "events": ["rain", "flood", "cyclone"]},
    {"id": "TVM01", "name": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366, "state": "Kerala",
     "events": ["rain", "cyclone", "thunderstorm"]},
    # --- East India ---
    {"id": "KOL01", "name": "Alipore (Kolkata)", "lat": 22.5726, "lon": 88.3639, "state": "West Bengal",
     "events": ["rain", "cyclone", "flood", "thunderstorm"]},
    {"id": "KOL02", "name": "Dum Dum (Kolkata)", "lat": 22.6520, "lon": 88.4470, "state": "West Bengal",
     "events": ["rain", "cyclone", "flood"]},
    {"id": "BBN01", "name": "Bhubaneswar", "lat": 20.2961, "lon": 85.8245, "state": "Odisha",
     "events": ["cyclone", "flood", "rain", "thunderstorm"]},
    {"id": "PAT01", "name": "Patna", "lat": 25.5941, "lon": 85.1376, "state": "Bihar",
     "events": ["rain", "flood", "fog", "thunderstorm"]},
    {"id": "GUW01", "name": "Borjhar (Guwahati)", "lat": 26.1445, "lon": 91.7362, "state": "Assam",
     "events": ["rain", "flood", "thunderstorm"]},
    # --- Northeast ---
    {"id": "SHI01", "name": "Shillong", "lat": 25.5788, "lon": 91.8933, "state": "Meghalaya",
     "events": ["rain", "flood", "thunderstorm", "hailstorm"]},
    # --- Andaman ---
    {"id": "PBL01", "name": "Port Blair", "lat": 11.6234, "lon": 92.7265, "state": "Andaman & Nicobar",
     "events": ["cyclone", "rain", "thunderstorm"]},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_station(lat: float, lon: float) -> Optional[dict]:
    """Return the nearest IMD station dict, or None if table is empty."""
    if not IMD_STATIONS:
        return None
    return min(
        IMD_STATIONS,
        key=lambda s: haversine_km(lat, lon, s["lat"], s["lon"])
    )


def geo_temporal_score(lat: float, lon: float, event_category: str) -> dict:
    """
    Section 3 — Step 3: Geo-temporal cross-reference score (0–30 points).

    Checks whether the nearest IMD station is known to experience the
    claimed event type, and how far away it is.

    Returns a dict with:
      score: float (0–30)
      station_name: str
      distance_km: float
      event_known_at_station: bool
      detail: str  (human-readable explanation shown in score breakdown)
    """
    station = nearest_station(lat, lon)
    if station is None:
        return {"score": 0.0, "station_name": "N/A", "distance_km": 9999,
                "event_known_at_station": False,
                "detail": "No IMD station reference data available."}

    dist_km = haversine_km(lat, lon, station["lat"], station["lon"])
    event_known = event_category.lower() in [e.lower() for e in station.get("events", [])]

    # Distance decay: full 30 pts within 25 km, linearly decays to 0 at 300 km
    MAX_DIST = 300.0
    FULL_DIST = 25.0
    if dist_km <= FULL_DIST:
        dist_factor = 1.0
    elif dist_km >= MAX_DIST:
        dist_factor = 0.0
    else:
        dist_factor = 1.0 - (dist_km - FULL_DIST) / (MAX_DIST - FULL_DIST)

    # Event type match multiplier
    event_factor = 1.0 if event_known else 0.35

    raw_score = 30.0 * dist_factor * event_factor
    score = round(max(0.0, min(30.0, raw_score)), 2)

    detail = (
        f"Nearest IMD station: {station['name']} ({station['state']}) — "
        f"{dist_km:.1f} km away. "
        f"Event '{event_category}' {'IS' if event_known else 'is NOT'} "
        f"on record for this station. "
        f"Distance factor: {dist_factor:.2f}, Event match: {event_factor:.2f}. "
        f"Geo score: {score}/30."
    )

    return {
        "score": score,
        "station_name": station["name"],
        "station_state": station["state"],
        "station_lat": station["lat"],
        "station_lon": station["lon"],
        "distance_km": round(dist_km, 2),
        "event_known_at_station": event_known,
        "detail": detail,
    }
