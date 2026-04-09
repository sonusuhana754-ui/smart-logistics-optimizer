"""
Shipment Automation & Scheduling Engine
Rule-based allocation: assigns shipments to vehicles automatically.
APScheduler runs allocation every 30 seconds.
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from automation.fleet_manager import fleet_manager


# ── Shipment Store (in-memory) ─────────────────────────────────────────
_shipments: Dict[str, dict] = {}
_manifests: List[dict] = []

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

CARGO_TYPES   = ["Electronics", "Perishable", "Hazardous", "General", "Fragile", "Bulk"]
PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]
CITY_NAMES = [
    "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata",
    "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]


def _seed_demo_shipments(n: int = 20):
    """Populate store with demo unscheduled shipments."""
    for i in range(n):
        cargo = random.choice(CARGO_TYPES)
        shp = {
            "shipment_id": f"SHP-{uuid.uuid4().hex[:8].upper()}",
            "origin": random.choice(CITY_NAMES),
            "destination": random.choice(CITY_NAMES),
            "cargo_type": cargo,
            "priority": random.choice(PRIORITY_LEVELS),
            "weight_kg": round(random.uniform(50, 8000), 1),
            "distance_km": round(random.uniform(150, 2200), 1),
            "status": "pending",
            "vehicle_id": None,
            "assigned_at": None,
            "estimated_departure": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        _shipments[shp["shipment_id"]] = shp


def get_all_shipments() -> List[dict]:
    return list(_shipments.values())


def get_shipment(shipment_id: str) -> Optional[dict]:
    return _shipments.get(shipment_id)


def add_shipment(data: dict) -> dict:
    sid = f"SHP-{uuid.uuid4().hex[:8].upper()}"
    shp = {
        "shipment_id": sid,
        "origin": data.get("origin", "Mumbai"),
        "destination": data.get("destination", "Delhi"),
        "cargo_type": data.get("cargo_type", "General"),
        "priority": data.get("priority", "Medium"),
        "weight_kg": float(data.get("weight_kg", 500)),
        "distance_km": float(data.get("distance_km", 500)),
        "status": "pending",
        "vehicle_id": None,
        "assigned_at": None,
        "estimated_departure": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    _shipments[sid] = shp
    return shp


def get_manifests() -> List[dict]:
    return list(_manifests)


# ── Allocation Engine ──────────────────────────────────────────────────

def run_allocation() -> dict:
    """
    Allocate all pending shipments to vehicles.
    Returns allocation report.
    """
    pending = [s for s in _shipments.values() if s["status"] == "pending"]
    if not pending:
        return {"allocated": 0, "unallocated": 0, "message": "No pending shipments."}

    # Sort by priority (Critical first)
    pending.sort(key=lambda s: PRIORITY_ORDER.get(s["priority"], 99))

    allocated = []
    unallocated = []
    manifest_entries = []

    for shp in pending:
        vehicle = fleet_manager.best_vehicle_for(shp["weight_kg"], shp["cargo_type"], shp["priority"])

        if vehicle is None:
            shp["status"] = "unallocated"
            unallocated.append(shp["shipment_id"])
            continue

        success = fleet_manager.assign_shipment(
            vehicle["vehicle_id"], shp["shipment_id"], shp["weight_kg"]
        )
        if not success:
            shp["status"] = "unallocated"
            unallocated.append(shp["shipment_id"])
            continue

        departure_dt = datetime.utcnow() + timedelta(hours=random.uniform(0.5, 4.0))
        shp["status"] = "allocated"
        shp["vehicle_id"] = vehicle["vehicle_id"]
        shp["assigned_at"] = datetime.utcnow().isoformat()
        shp["estimated_departure"] = departure_dt.isoformat()
        allocated.append(shp["shipment_id"])

        manifest_entries.append({
            "manifest_id": f"MFT-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": shp["shipment_id"],
            "vehicle_id": vehicle["vehicle_id"],
            "vehicle_type": vehicle["vehicle_type"],
            "origin": shp["origin"],
            "destination": shp["destination"],
            "cargo_type": shp["cargo_type"],
            "priority": shp["priority"],
            "weight_kg": shp["weight_kg"],
            "estimated_departure": shp["estimated_departure"],
            "created_at": datetime.utcnow().isoformat(),
        })

    _manifests.extend(manifest_entries)

    report = {
        "allocated": len(allocated),
        "unallocated": len(unallocated),
        "allocated_ids": allocated,
        "unallocated_ids": unallocated,
        "new_manifests": manifest_entries,
        "timestamp": datetime.utcnow().isoformat(),
    }
    print(f"✅ Allocation run: {len(allocated)} allocated, {len(unallocated)} unallocated.")
    return report


def _auto_refresh_shipments():
    """Periodically add a few new demo shipments to simulate incoming orders."""
    n_new = random.randint(1, 3)
    pending_count = sum(1 for s in _shipments.values() if s["status"] == "pending")
    if pending_count < 5:
        _seed_demo_shipments(n_new)

    # Also auto-release some dispatched vehicles to simulate deliveries
    dispatched = [s for s in _shipments.values() if s["status"] == "allocated"]
    for shp in dispatched[:2]:
        if random.random() < 0.3:
            if shp["vehicle_id"]:
                fleet_manager.release_vehicle(shp["vehicle_id"], shp["shipment_id"], shp["weight_kg"])
            shp["status"] = "delivered"


# ── APScheduler ────────────────────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler():
    global _scheduler
    fleet_manager.initialize()
    _seed_demo_shipments(20)

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_allocation,         "interval", seconds=30, id="auto_allocate")
    _scheduler.add_job(_auto_refresh_shipments, "interval", seconds=45, id="refresh_shipments")
    _scheduler.start()
    print("✅ Automation scheduler started (30s allocation, 45s refresh).")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
