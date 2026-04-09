"""
Route Optimization Engine
Implements Dijkstra, A*, and multi-stop VRP-style optimization.
Supports dynamic re-routing when anomalies are detected.
"""

import heapq
import math
from typing import Dict, List, Optional, Tuple
from routing.graph_builder import build_graph, get_city_coords, CITIES


def _heuristic(city_a: str, city_b: str) -> float:
    """A* heuristic: straight-line distance between two cities (km)."""
    coords = get_city_coords()
    if city_a not in coords or city_b not in coords:
        return 0.0
    lat1, lon1 = coords[city_a]
    lat2, lon2 = coords[city_b]
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def dijkstra(
    graph: Dict,
    origin: str,
    destination: str,
    weight_key: str = "distance_km",
) -> Tuple[List[str], float]:
    """
    Dijkstra's algorithm.
    Returns (path, total_weight) or ([], inf) if no path exists.
    """
    if origin not in graph or destination not in graph:
        return [], float("inf")

    dist = {city: float("inf") for city in graph}
    dist[origin] = 0.0
    prev: Dict[str, Optional[str]] = {city: None for city in graph}
    pq = [(0.0, origin)]

    while pq:
        current_cost, current = heapq.heappop(pq)
        if current == destination:
            break
        if current_cost > dist[current]:
            continue
        for neighbor, edge in graph[current].items():
            w = edge.get(weight_key, 1.0)
            new_cost = dist[current] + w
            if new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                prev[neighbor] = current
                heapq.heappush(pq, (new_cost, neighbor))

    # Reconstruct path
    if dist[destination] == float("inf"):
        return [], float("inf")

    path = []
    node = destination
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path, dist[destination]


def astar(
    graph: Dict,
    origin: str,
    destination: str,
    weight_key: str = "time_h",
) -> Tuple[List[str], float]:
    """
    A* search optimized for time.
    Returns (path, total_time_h).
    """
    if origin not in graph or destination not in graph:
        return [], float("inf")

    g_score = {city: float("inf") for city in graph}
    g_score[origin] = 0.0
    f_score = {city: float("inf") for city in graph}
    f_score[origin] = _heuristic(origin, destination) / 65.0  # km -> approx hours

    prev: Dict[str, Optional[str]] = {city: None for city in graph}
    open_set = [(f_score[origin], origin)]
    closed_set: set = set()

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == destination:
            break
        if current in closed_set:
            continue
        closed_set.add(current)

        for neighbor, edge in graph[current].items():
            if neighbor in closed_set:
                continue
            tentative_g = g_score[current] + edge.get(weight_key, 1.0)
            if tentative_g < g_score[neighbor]:
                prev[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + _heuristic(neighbor, destination) / 65.0
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    if g_score[destination] == float("inf"):
        return [], float("inf")

    path = []
    node = destination
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path, g_score[destination]


def _path_metrics(graph: Dict, path: List[str]) -> dict:
    """Aggregate distance, time, and cost for a given path."""
    total_distance = 0.0
    total_time = 0.0
    total_cost = 0.0
    waypoints = []

    coords = get_city_coords()

    for i, city in enumerate(path):
        lat, lon = coords.get(city, (0.0, 0.0))
        waypoints.append({"city": city, "lat": lat, "lon": lon, "index": i})

        if i < len(path) - 1:
            next_city = path[i + 1]
            edge = graph.get(city, {}).get(next_city, {})
            total_distance += edge.get("distance_km", 0.0)
            total_time += edge.get("time_h", 0.0)
            total_cost += edge.get("cost", 0.0)

    return {
        "path": path,
        "waypoints": waypoints,
        "total_distance_km": round(total_distance, 2),
        "total_time_h": round(total_time, 3),
        "estimated_cost": round(total_cost, 2),
    }


def optimize_route(
    origin: str,
    destination: str,
    traffic_density: float = 30.0,
    weather_severity: float = 0.0,
    optimization_mode: str = "balanced",  # "distance" | "time" | "cost" | "balanced"
    delay_probability: float = 0.0,
    eco_mode: bool = False,
    avoid_bbox: Optional[List[float]] = None,
) -> dict:
    """
    Main route optimization entry point.
    Returns primary route + 2 alternative routes.
    Triggers re-routing if delay_probability > 0.6.
    """
    graph = build_graph(
        traffic_density=traffic_density, 
        weather_severity=weather_severity,
        eco_mode=eco_mode,
        avoid_bbox=avoid_bbox
    )

    if origin not in graph:
        return {"error": f"Unknown origin city: {origin}"}
    if destination not in graph:
        return {"error": f"Unknown destination city: {destination}"}

    # Dynamic re-routing: use time-optimized A* if high delay risk
    rerouted = delay_probability > 0.60
    if rerouted:
        optimization_mode = "time"

    # ── Primary Route ──────────────────────────────────────────────────
    if optimization_mode == "distance":
        primary_path, _ = dijkstra(graph, origin, destination, "distance_km")
    elif optimization_mode == "time":
        primary_path, _ = astar(graph, origin, destination, "time_h")
    elif optimization_mode == "cost":
        primary_path, _ = dijkstra(graph, origin, destination, "cost")
    else:  # balanced — minimize composite score
        # Combined weight = 0.4*time + 0.3*distance/100 + 0.3*cost/1000 (normalised)
        # Build temp graph with composite weights
        composite_graph: Dict = {}
        for city, neighbors in graph.items():
            composite_graph[city] = {}
            for nb, edge in neighbors.items():
                composite_graph[city][nb] = {
                    **edge,
                    "composite": (
                        edge["time_h"] * 0.4
                        + edge["distance_km"] / 100 * 0.3
                        + edge["cost"] / 1000 * 0.3
                    ),
                }
        primary_path, _ = dijkstra(composite_graph, origin, destination, "composite")

    if not primary_path:
        return {"error": "No route found between origin and destination."}

    primary = _path_metrics(graph, primary_path)
    primary["route_type"] = "primary"
    primary["optimization_mode"] = optimization_mode if not rerouted else "time"
    primary["rerouted_due_to_anomaly"] = rerouted

    # ── Alternative 1: pure shortest distance ─────────────────────────
    alt1_path, _ = dijkstra(graph, origin, destination, "distance_km")
    alt1 = _path_metrics(graph, alt1_path)
    alt1["route_type"] = "alternative_1_shortest"

    # ── Alternative 2: pure fastest time ──────────────────────────────
    alt2_path, _ = astar(graph, origin, destination, "time_h")
    alt2 = _path_metrics(graph, alt2_path)
    alt2["route_type"] = "alternative_2_fastest"

    # ── Comparison metrics ─────────────────────────────────────────────
    baseline_time_h = primary["total_time_h"]
    baseline_dist = primary["total_distance_km"]

    return {
        "origin": origin,
        "destination": destination,
        "optimization_mode": optimization_mode,
        "rerouted_due_to_anomaly": rerouted,
        "conditions": {
            "traffic_density": traffic_density,
            "weather_severity": weather_severity,
            "delay_probability": delay_probability,
        },
        "primary_route": primary,
        "alternatives": [alt1, alt2],
        "efficiency_vs_baseline": {
            "time_saving_pct": round(
                (1 - primary["total_time_h"] / max(alt1["total_time_h"], 0.001)) * 100, 1
            ),
            "distance_saving_pct": round(
                (1 - primary["total_distance_km"] / max(alt1["total_distance_km"], 0.001)) * 100, 1
            ),
        },
    }


def multi_stop_vrp(
    depot: str,
    stops: List[str],
    traffic_density: float = 30.0,
    weather_severity: float = 0.0,
) -> dict:
    """
    Simplified VRP: greedy nearest-neighbor heuristic for multi-stop routing.
    Returns ordered stop sequence and per-leg metrics.
    """
    graph = build_graph(traffic_density=traffic_density, weather_severity=weather_severity)

    if not stops:
        return {"error": "No stops provided."}

    remaining = list(stops)
    current = depot
    ordered_stops = [depot]
    legs: List[dict] = []
    total_distance = 0.0
    total_time = 0.0
    total_cost = 0.0

    while remaining:
        best_city = None
        best_dist = float("inf")
        best_path = []

        for city in remaining:
            path, dist = dijkstra(graph, current, city, "distance_km")
            if dist < best_dist:
                best_dist = dist
                best_city = city
                best_path = path

        if best_city is None:
            break

        metrics = _path_metrics(graph, best_path)
        legs.append({
            "from": current,
            "to": best_city,
            **metrics,
        })
        total_distance += metrics["total_distance_km"]
        total_time += metrics["total_time_h"]
        total_cost += metrics["estimated_cost"]

        ordered_stops.append(best_city)
        current = best_city
        remaining.remove(best_city)

    return {
        "depot": depot,
        "ordered_stops": ordered_stops,
        "legs": legs,
        "total_distance_km": round(total_distance, 2),
        "total_time_h": round(total_time, 3),
        "total_estimated_cost": round(total_cost, 2),
    }
