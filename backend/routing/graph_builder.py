"""
City Graph Builder
Constructs a weighted road network graph for route optimization.
Nodes = Indian cities with realistic lat/lon coordinates.
Edges = road segments with distance, congestion, and time weights.
"""

import math
from typing import Dict, List, Tuple, Optional


# ── City Registry ──────────────────────────────────────────────────────
CITIES: Dict[str, Tuple[float, float]] = {
    "Mumbai":           (19.0760, 72.8777),
    "Delhi":            (28.6139, 77.2090),
    "Bangalore":        (12.9716, 77.5946),
    "Chennai":          (13.0827, 80.2707),
    "Kolkata":          (22.5726, 88.3639),
    "Hyderabad":        (17.3850, 78.4867),
    "Pune":             (18.5204, 73.8567),
    "Ahmedabad":        (23.0225, 72.5714),
    "Jaipur":           (26.9124, 75.7873),
    "Lucknow":          (26.8467, 80.9462),
    "Surat":            (21.1702, 72.8311),
    "Kochi":            (9.9312,  76.2673),
    "Bhubaneswar":      (20.2961, 85.8245),
    "Coimbatore":       (11.0168, 76.9558),
    "Goa":              (15.2993, 74.1240),
    "Chandigarh":       (30.7333, 76.7794),
    "Nagpur":           (21.1458, 79.0882),
    "Indore":           (22.7196, 75.8577),
    "Bhopal":           (23.2599, 77.4126),
    "Visakhapatnam":    (17.6868, 83.2185),
}

# ── Road Segments ──────────────────────────────────────────────────────
# (city_a, city_b, distance_km, base_congestion_factor)
ROAD_SEGMENTS: List[Tuple[str, str, float, float]] = [
    ("Mumbai",      "Pune",         150,  1.20),
    ("Mumbai",      "Surat",        265,  1.10),
    ("Mumbai",      "Ahmedabad",    535,  1.05),
    ("Mumbai",      "Nagpur",       835,  1.00),
    ("Mumbai",      "Goa",          590,  1.00),
    ("Pune",        "Hyderabad",    565,  1.00),
    ("Pune",        "Bangalore",    840,  1.00),
    ("Pune",        "Goa",          460,  1.00),
    ("Ahmedabad",   "Jaipur",       645,  1.05),
    ("Ahmedabad",   "Surat",        265,  1.10),
    ("Ahmedabad",   "Indore",       395,  1.00),
    ("Delhi",       "Jaipur",       275,  1.15),
    ("Delhi",       "Chandigarh",   250,  1.10),
    ("Delhi",       "Lucknow",      555,  1.10),
    ("Delhi",       "Nagpur",      1095,  1.00),
    ("Delhi",       "Bhopal",       777,  1.00),
    ("Jaipur",      "Lucknow",      585,  1.00),
    ("Lucknow",     "Kolkata",      980,  1.00),
    ("Kolkata",     "Bhubaneswar",  440,  1.05),
    ("Bhubaneswar", "Visakhapatnam",420,  1.00),
    ("Visakhapatnam","Hyderabad",   580,  1.00),
    ("Hyderabad",   "Bangalore",    570,  1.05),
    ("Hyderabad",   "Chennai",      630,  1.05),
    ("Hyderabad",   "Nagpur",       500,  1.00),
    ("Bangalore",   "Chennai",      350,  1.15),
    ("Bangalore",   "Coimbatore",   360,  1.05),
    ("Bangalore",   "Kochi",        540,  1.00),
    ("Chennai",     "Coimbatore",   500,  1.05),
    ("Chennai",     "Kochi",        690,  1.00),
    ("Nagpur",      "Bhopal",       360,  1.00),
    ("Nagpur",      "Indore",       475,  1.00),
    ("Bhopal",      "Indore",       195,  1.05),
    ("Indore",      "Mumbai",       590,  1.00),
    ("Chandigarh",  "Delhi",        250,  1.10),
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_graph(
    traffic_density: float = 30.0,
    weather_severity: float = 0.0,
    eco_mode: bool = False,
    avoid_bbox: Optional[List[float]] = None,
) -> Dict[str, Dict[str, dict]]:
    """
    Build weighted adjacency graph.
    Returns: { city: { neighbor: { distance, time, cost, weight } } }
    
    Edge weights are adjusted by real-time conditions.
    """
    avg_speed_kmh = 65.0
    rt_slowdown = 1.0 + (weather_severity * 0.35) + (traffic_density / 100.0 * 0.30)

    graph: Dict[str, Dict[str, dict]] = {city: {} for city in CITIES}

    for city_a, city_b, dist_km, cong in ROAD_SEGMENTS:
        if city_a not in CITIES or city_b not in CITIES:
            continue
            
        # Geofencing: Check if node falls in avoid_bbox [min_lon, min_lat, max_lon, max_lat]
        avoid_edge = False
        if avoid_bbox and len(avoid_bbox) == 4:
            min_lon, min_lat, max_lon, max_lat = avoid_bbox
            lat_a, lon_a = CITIES[city_a]
            lat_b, lon_b = CITIES[city_b]
            if (min_lat <= lat_a <= max_lat and min_lon <= lon_a <= max_lon) or \
               (min_lat <= lat_b <= max_lat and min_lon <= lon_b <= max_lon):
                avoid_edge = True

        # Eco Mode Penalty: heavily penalize routes with high base congestion and current traffic
        eco_penalty = 1.0
        if eco_mode:
            eco_penalty += (cong - 1.0) * 2.0  # Avoid historically congested route
            eco_penalty += (traffic_density / 100.0) * 1.5 # Avoid live traffic (idling)

        effective_speed = avg_speed_kmh / (cong * rt_slowdown)
        time_h = (dist_km / effective_speed) * eco_penalty
        cost = dist_km * 18 * cong * (1 + weather_severity * 0.2)
        
        # If avoids polygon, weight becomes infinity
        if avoid_edge:
            dist_km = float('inf')
            time_h = float('inf')

        edge = {
            "distance_km": dist_km if avoid_edge else round(dist_km, 1),
            "time_h": time_h if avoid_edge else round(time_h, 3),
            "cost": float('inf') if avoid_edge else round(cost, 2),
            "congestion_factor": cong,
        }
        graph[city_a][city_b] = edge
        graph[city_b][city_a] = edge  # bidirectional

    return graph


def get_all_cities() -> List[str]:
    return sorted(CITIES.keys())


def get_city_coords() -> Dict[str, Tuple[float, float]]:
    return dict(CITIES)
