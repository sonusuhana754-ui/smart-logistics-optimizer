"""
Supply Chain Dataset Generator
Generates synthetic but statistically realistic historical shipment data
mirroring the Kaggle Supply Chain dataset schema.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os

# ── Seeds for reproducibility ──────────────────────────────────────────
np.random.seed(42)
random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────
CARGO_TYPES = ["Electronics", "Perishable", "Hazardous", "General", "Fragile", "Bulk"]
PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]
WEATHER_CONDITIONS = ["Clear", "Rain", "Fog", "Storm", "Snow"]
CARRIERS = ["FastFreight", "GlobalLogix", "SwiftCargo", "PrimeShip", "EcoMove"]
VEHICLE_TYPES = ["Van", "Truck", "Heavy Truck", "Refrigerated", "Flatbed"]

CITY_PAIRS = [
    ("Mumbai", "Delhi", 1400),
    ("Delhi", "Bangalore", 2150),
    ("Bangalore", "Chennai", 350),
    ("Mumbai", "Pune", 150),
    ("Delhi", "Kolkata", 1480),
    ("Hyderabad", "Chennai", 630),
    ("Mumbai", "Ahmedabad", 530),
    ("Kolkata", "Bhubaneswar", 440),
    ("Jaipur", "Delhi", 270),
    ("Lucknow", "Kanpur", 90),
    ("Chennai", "Coimbatore", 500),
    ("Pune", "Goa", 450),
    ("Hyderabad", "Bangalore", 570),
    ("Ahmedabad", "Surat", 260),
    ("Kochi", "Thiruvananthapuram", 220),
]


def generate_supply_chain_data(n_records: int = 10000) -> pd.DataFrame:
    """Generate n_records of synthetic supply chain shipment history."""

    records = []
    base_date = datetime(2023, 1, 1)

    for i in range(n_records):
        # ── Route ──────────────────────────────────────────────────────
        origin, destination, base_distance = random.choice(CITY_PAIRS)
        distance_km = base_distance * np.random.uniform(0.9, 1.1)

        # ── Shipment attributes ────────────────────────────────────────
        cargo_type = random.choice(CARGO_TYPES)
        priority = random.choice(PRIORITY_LEVELS)
        weight_kg = np.random.lognormal(mean=5.0, sigma=1.2)
        weight_kg = float(np.clip(weight_kg, 10, 20000))

        vehicle_type = random.choice(VEHICLE_TYPES)
        carrier = random.choice(CARRIERS)

        # ── Temporal features ──────────────────────────────────────────
        departure_dt = base_date + timedelta(
            days=random.randint(0, 365 * 2),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        day_of_week = departure_dt.weekday()   # 0=Mon, 6=Sun
        hour_of_day = departure_dt.hour
        is_peak_hour = 1 if hour_of_day in range(8, 11) or hour_of_day in range(17, 20) else 0
        is_weekend = 1 if day_of_week >= 5 else 0

        # ── Real-time conditions at departure ──────────────────────────
        weather = random.choice(WEATHER_CONDITIONS)
        weather_severity = {
            "Clear": 0.0, "Rain": 0.3, "Fog": 0.5, "Storm": 0.8, "Snow": 0.9
        }[weather]

        traffic_density = np.random.beta(2, 5) * 100  # 0-100 scale
        if is_peak_hour:
            traffic_density = min(100, traffic_density * 1.5)

        # ── Speed & duration model ─────────────────────────────────────
        base_speed_kmh = 65.0  # average highway speed

        # Multiplicative delay factors
        weather_slow = 1 + weather_severity * 0.4
        traffic_slow = 1 + (traffic_density / 100) * 0.5
        cargo_factor = {
            "Electronics": 1.0, "Perishable": 1.1, "Hazardous": 1.3,
            "General": 1.0, "Fragile": 1.15, "Bulk": 1.05
        }[cargo_type]
        weight_factor = 1 + (weight_kg / 20000) * 0.2

        effective_speed = base_speed_kmh / (weather_slow * traffic_slow * cargo_factor * weight_factor)
        base_duration_h = distance_km / effective_speed

        # Add random noise + carrier performance variation
        carrier_perf = {
            "FastFreight": 0.92, "GlobalLogix": 1.05, "SwiftCargo": 0.95,
            "PrimeShip": 0.98, "EcoMove": 1.10
        }[carrier]
        actual_duration_h = base_duration_h * carrier_perf * np.random.uniform(0.85, 1.25)

        # ── Delay determination ────────────────────────────────────────
        delay_probability = (
            0.10
            + weather_severity * 0.25
            + (traffic_density / 100) * 0.20
            + is_peak_hour * 0.08
            + (1 if cargo_type == "Hazardous" else 0) * 0.10
        )
        delay_probability = float(np.clip(delay_probability, 0.02, 0.95))
        is_delayed = 1 if random.random() < delay_probability else 0
        delay_minutes = np.random.exponential(45) * is_delayed

        # ── Cost estimation ────────────────────────────────────────────
        base_cost_per_km = {
            "Van": 12, "Truck": 22, "Heavy Truck": 35,
            "Refrigerated": 30, "Flatbed": 28
        }[vehicle_type]

        cost_factor = (
            base_cost_per_km * distance_km / 1000
            + weight_kg * 0.002
            + delay_minutes * 0.5
            + weather_severity * 200
        )
        cost_factor = float(np.clip(cost_factor, 5.0, 5000.0))

        # ── Arrival timestamp ──────────────────────────────────────────
        arrival_dt = departure_dt + timedelta(hours=actual_duration_h, minutes=delay_minutes)

        records.append({
            "shipment_id": f"SHP{i+1:06d}",
            "origin": origin,
            "destination": destination,
            "distance_km": round(distance_km, 2),
            "cargo_type": cargo_type,
            "priority": priority,
            "weight_kg": round(weight_kg, 2),
            "vehicle_type": vehicle_type,
            "carrier": carrier,
            "departure_datetime": departure_dt.isoformat(),
            "arrival_datetime": arrival_dt.isoformat(),
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "is_peak_hour": is_peak_hour,
            "is_weekend": is_weekend,
            "weather_condition": weather,
            "weather_severity": round(weather_severity, 3),
            "traffic_density": round(float(traffic_density), 2),
            "actual_duration_hours": round(actual_duration_h, 4),
            "delay_minutes": round(float(delay_minutes), 2),
            "is_delayed": is_delayed,
            "delay_probability": round(delay_probability, 4),
            "cost_factor": round(cost_factor, 2),
        })

    df = pd.DataFrame(records)
    return df


def save_dataset(output_path: str = None) -> str:
    """Generate and save the supply chain dataset, return path."""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "supply_chain_data.csv")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = generate_supply_chain_data(10000)
    df.to_csv(output_path, index=False)
    print(f"✅ Dataset saved: {output_path}  ({len(df)} records)")
    return output_path


if __name__ == "__main__":
    save_dataset()
