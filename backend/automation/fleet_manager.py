"""
Fleet Manager
Maintains the virtual vehicle fleet — types, capacities, availability, and load.
"""

import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional

# ── Vehicle Definitions ────────────────────────────────────────────────
VEHICLE_SPECS = {
    "Van":           {"capacity_kg": 1000,  "cost_per_km": 12, "max_range_km": 600},
    "Truck":         {"capacity_kg": 8000,  "cost_per_km": 22, "max_range_km": 1500},
    "Heavy Truck":   {"capacity_kg": 20000, "cost_per_km": 35, "max_range_km": 2500},
    "Refrigerated":  {"capacity_kg": 5000,  "cost_per_km": 30, "max_range_km": 1200},
    "Flatbed":       {"capacity_kg": 15000, "cost_per_km": 28, "max_range_km": 2000},
}


def _make_vehicle(vehicle_type: str, index: int) -> dict:
    spec = VEHICLE_SPECS[vehicle_type]
    return {
        "vehicle_id": f"VH-{vehicle_type[:2].upper()}-{index:03d}",
        "vehicle_type": vehicle_type,
        "capacity_kg": spec["capacity_kg"],
        "cost_per_km": spec["cost_per_km"],
        "max_range_km": spec["max_range_km"],
        "current_load_kg": 0.0,
        "available_capacity_kg": spec["capacity_kg"],
        "status": "available",        # available | dispatched | maintenance
        "current_location": random.choice([
            "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune"
        ]),
        "assigned_shipment_ids": [],
        "total_km_driven": round(random.uniform(0, 50000), 1),
        "maintenance_flag": False,
        "last_updated": datetime.utcnow().isoformat(),
    }


class FleetManager:
    """Singleton fleet state manager."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return
        self._fleet: Dict[str, dict] = {}
        # Spin up initial fleet
        counts = {"Van": 5, "Truck": 6, "Heavy Truck": 3, "Refrigerated": 3, "Flatbed": 3}
        for vtype, count in counts.items():
            for i in range(1, count + 1):
                v = _make_vehicle(vtype, i)
                if v["vehicle_id"] == "VH-TR-002" or v["vehicle_id"] == "VH-RE-001":
                    v["maintenance_flag"] = True
                self._fleet[v["vehicle_id"]] = v
        self._initialized = True
        print(f"✅ Fleet initialized: {len(self._fleet)} vehicles")

    # ── Queries ────────────────────────────────────────────────────────

    def get_all_vehicles(self) -> List[dict]:
        return list(self._fleet.values())

    def get_available_vehicles(self, min_capacity_kg: float = 0.0) -> List[dict]:
        return [
            v for v in self._fleet.values()
            if v["status"] == "available" and v["available_capacity_kg"] >= min_capacity_kg
        ]

    def get_vehicle(self, vehicle_id: str) -> Optional[dict]:
        return self._fleet.get(vehicle_id)

    def get_fleet_summary(self) -> dict:
        vehicles = list(self._fleet.values())
        available  = [v for v in vehicles if v["status"] == "available"]
        dispatched = [v for v in vehicles if v["status"] == "dispatched"]
        maintenance= [v for v in vehicles if v["status"] == "maintenance"]

        total_cap = sum(v["capacity_kg"] for v in available)
        utilized  = sum(v["current_load_kg"] for v in dispatched)
        total_dispatched_cap = sum(v["capacity_kg"] for v in dispatched) or 1

        return {
            "total_vehicles": len(vehicles),
            "available": len(available),
            "dispatched": len(dispatched),
            "maintenance": len(maintenance),
            "utilization_pct": round(utilized / total_dispatched_cap * 100, 1) if dispatched else 0.0,
            "available_capacity_kg": total_cap,
            "vehicles": vehicles,
        }

    # ── Mutations ──────────────────────────────────────────────────────

    def assign_shipment(self, vehicle_id: str, shipment_id: str, load_kg: float) -> bool:
        v = self._fleet.get(vehicle_id)
        if not v or v["status"] != "available":
            return False
        if v["available_capacity_kg"] < load_kg:
            return False

        v["current_load_kg"] += load_kg
        v["available_capacity_kg"] -= load_kg
        v["assigned_shipment_ids"].append(shipment_id)
        v["status"] = "dispatched"
        v["last_updated"] = datetime.utcnow().isoformat()
        return True

    def release_vehicle(self, vehicle_id: str, shipment_id: str, load_kg: float):
        v = self._fleet.get(vehicle_id)
        if not v:
            return
        v["current_load_kg"] = max(0, v["current_load_kg"] - load_kg)
        v["available_capacity_kg"] = v["capacity_kg"] - v["current_load_kg"]
        if shipment_id in v["assigned_shipment_ids"]:
            v["assigned_shipment_ids"].remove(shipment_id)
        if not v["assigned_shipment_ids"]:
            v["status"] = "available"
        v["last_updated"] = datetime.utcnow().isoformat()

    def best_vehicle_for(self, weight_kg: float, cargo_type: str, priority: str = "Medium") -> Optional[dict]:
        """Select the best available vehicle for a given shipment."""
        candidates = self.get_available_vehicles(min_capacity_kg=weight_kg)
        
        # Predictive Fleet Health check
        if priority in ["Critical", "High"]:
            safe_candidates = [v for v in candidates if not v.get("maintenance_flag")]
            if candidates and not safe_candidates:
                print(f"⚠️ Risk: All available vehicles for this {priority} load show signs of impending maintenance needs!")
            elif safe_candidates:
                candidates = safe_candidates

        if not candidates:
            return None

        # Prefer Refrigerated for Perishable
        if cargo_type == "Perishable":
            fridge = [v for v in candidates if v["vehicle_type"] == "Refrigerated"]
            if fridge:
                return min(fridge, key=lambda v: v["cost_per_km"])

        # Prefer smallest vehicle that fits (minimize waste)
        candidates.sort(key=lambda v: v["capacity_kg"])
        return candidates[0]

    def trigger_swarm_mode(self) -> dict:
        """Pre-position idle fleet to predicted demand hotspots."""
        hubs = ["Mumbai", "Delhi", "Bangalore", "Chennai"]  # Kaggle historical clusters
        available = self.get_available_vehicles()
        moved = 0
        for v in available:
            v["status"] = "Pre-positioned"
            v["current_location"] = random.choice(hubs)
            v["last_updated"] = datetime.utcnow().isoformat()
            moved += 1
        return {"message": f"Swarm mode active: {moved} idle vehicles pre-positioned to high demand hubs.", "hubs": hubs}


# Module-level singleton
fleet_manager = FleetManager()
