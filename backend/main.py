"""
FastAPI Main Application
AI-Powered Intelligent Logistics Optimization System — Backend API
"""

import asyncio
import json
import queue
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

import sys
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

load_dotenv()

# Fix import paths
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ── Internal modules ───────────────────────────────────────────────────
from data.realtime_simulator import simulator
from ml.predictor import prediction_engine
from routing.optimizer import optimize_route, multi_stop_vrp
from routing.graph_builder import get_all_cities, get_city_coords
from automation.scheduler import (
    start_scheduler, stop_scheduler,
    get_all_shipments, get_shipment, add_shipment,
    run_allocation, get_manifests,
)
from automation.fleet_manager import fleet_manager

# ── Lifespan (replaces deprecated on_event for FastAPI 0.112+) ────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting AI Logistics System…")
    simulator.start()
    prediction_engine.load_models()
    fleet_manager.initialize()
    start_scheduler()
    print("✅ All systems online.")
    yield
    simulator.stop()
    stop_scheduler()

# ══════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="AI Logistics Optimization API",
    version="1.0.0",
    description="Prediction Engine + Route Optimization + Shipment Automation",
    lifespan=lifespan,
)
@app.get("/")
def root():
    return {
        "status": "running",
        "message": "AI Logistics Optimization API",
        "docs": "/docs",
        "health": "/api/health"
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
        "https://smart-logistics-optimizer.vercel.app",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
#  PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════

class PredictionRequest(BaseModel):
    origin: str = "Mumbai"
    destination: str = "Delhi"
    distance_km: float = Field(1400, gt=0)
    cargo_type: str = "General"
    priority: str = "Medium"
    weight_kg: float = Field(500, gt=0)
    vehicle_type: str = "Truck"
    carrier: str = "FastFreight"
    departure_datetime: str = ""
    # Real-time override (if not provided, use simulator values)
    weather_condition: Optional[str] = None
    weather_severity: Optional[float] = None
    traffic_density: Optional[float] = None


class RouteRequest(BaseModel):
    origin: str = "Mumbai"
    destination: str = "Delhi"
    optimization_mode: str = "balanced"   # distance | time | cost | balanced
    eco_mode: bool = False
    avoid_bbox: Optional[list[float]] = None
    # Real-time override
    traffic_density: Optional[float] = None
    weather_severity: Optional[float] = None
    delay_probability: float = 0.0


class MultiStopRequest(BaseModel):
    depot: str = "Mumbai"
    stops: list[str] = ["Delhi", "Jaipur", "Lucknow"]
    traffic_density: Optional[float] = None
    weather_severity: Optional[float] = None


class ShipmentCreateRequest(BaseModel):
    origin: str = "Mumbai"
    destination: str = "Delhi"
    cargo_type: str = "General"
    priority: str = "Medium"
    weight_kg: float = 500.0
    distance_km: float = 1400.0


class AnomalyRequest(BaseModel):
    anomaly_type: str = "traffic_spike"   # traffic_spike | severe_weather | combined
    duration_s: float = 60.0

class JarvisRequest(BaseModel):
    command: str


# ══════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "modules": {
            "prediction_engine": "loaded" if prediction_engine._loaded else "loading",
            "realtime_simulator": "running",
            "fleet_manager": "initialized" if fleet_manager._initialized else "pending",
        },
    }


# ══════════════════════════════════════════════════════════════════════
#  PREDICTION ENGINE
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/predict")
def predict(req: PredictionRequest):
    """Run ETA + Delay + Cost prediction for a shipment."""
    rt = simulator.get_current_state()

    departure = req.departure_datetime or datetime.utcnow().isoformat()
    weather_condition = req.weather_condition or rt["weather_condition"]
    weather_severity  = req.weather_severity  if req.weather_severity  is not None else rt["weather_severity"]
    traffic_density   = req.traffic_density   if req.traffic_density   is not None else rt["traffic_density"]

    try:
        result = prediction_engine.predict(
            origin=req.origin,
            destination=req.destination,
            distance_km=req.distance_km,
            cargo_type=req.cargo_type,
            priority=req.priority,
            weight_kg=req.weight_kg,
            vehicle_type=req.vehicle_type,
            carrier=req.carrier,
            departure_datetime=departure,
            weather_condition=weather_condition,
            weather_severity=weather_severity,
            traffic_density=traffic_density,
        )
        result["realtime_conditions"] = rt
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/predict/metrics")
def model_metrics():
    """Return trained model performance metrics."""
    return prediction_engine.get_model_metrics()


# ══════════════════════════════════════════════════════════════════════
#  ROUTE OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/optimize-route")
def optimize(req: RouteRequest):
    """Compute optimized routes between two cities."""
    rt = simulator.get_current_state()
    traffic = req.traffic_density if req.traffic_density is not None else rt["traffic_density"]
    weather = req.weather_severity if req.weather_severity is not None else rt["weather_severity"]

    result = optimize_route(
        origin=req.origin,
        destination=req.destination,
        traffic_density=traffic,
        weather_severity=weather,
        optimization_mode=req.optimization_mode,
        delay_probability=req.delay_probability,
        eco_mode=req.eco_mode,
        avoid_bbox=req.avoid_bbox,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    result["realtime_conditions"] = rt
    return result


@app.post("/api/optimize-route/multi-stop")
def multi_stop(req: MultiStopRequest):
    """Multi-stop VRP route optimization."""
    rt = simulator.get_current_state()
    traffic = req.traffic_density if req.traffic_density is not None else rt["traffic_density"]
    weather = req.weather_severity if req.weather_severity is not None else rt["weather_severity"]

    result = multi_stop_vrp(
        depot=req.depot,
        stops=req.stops,
        traffic_density=traffic,
        weather_severity=weather,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/cities")
def list_cities():
    """Return all available city names and coordinates."""
    return {
        "cities": get_all_cities(),
        "coordinates": get_city_coords(),
    }


# ══════════════════════════════════════════════════════════════════════
#  SHIPMENT MANAGEMENT & AUTOMATION
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/shipments")
def list_shipments(status: Optional[str] = None):
    """List all shipments, optionally filtered by status."""
    shipments = get_all_shipments()
    if status:
        shipments = [s for s in shipments if s["status"] == status]
    return {"shipments": shipments, "total": len(shipments)}


@app.post("/api/shipments")
def create_shipment(req: ShipmentCreateRequest):
    """Add a new shipment to the pending queue."""
    shp = add_shipment(req.dict())
    return {"message": "Shipment added.", "shipment": shp}


@app.get("/api/shipments/{shipment_id}")
def get_shipment_detail(shipment_id: str):
    shp = get_shipment(shipment_id)
    if not shp:
        raise HTTPException(status_code=404, detail="Shipment not found.")
    return shp


@app.post("/api/automate")
def trigger_allocation():
    """Manually trigger the shipment auto-allocation engine."""
    report = run_allocation()
    return report

@app.post("/api/jarvis")
def jarvis_dispatch(req: JarvisRequest):
    """LLM-Powered Voice/Text Dispatch using Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in environment.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    You are Jarvis, an advanced AI Logistics Dispatcher.
    Extract the intent from the following user command: "{req.command}"
    
    You must output exactly this JSON schema and absolutely nothing else:
    {{
      "action": "reroute" | "hold" | "allocate",
      "condition": "storm" | "traffic" | "none",
      "priority": "Critical" | "High" | "Medium" | "Low" | "All"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        intent = json.loads(text)
        
        # Execute logic dynamically based on LLM intent
        from automation.scheduler import _shipments
        message = "Jarvis: Processing command."
        
        if intent["action"] == "reroute":
            # Fire an anomaly and force allocation
            a_type = "severe_weather" if intent["condition"] == "storm" else "traffic_spike"
            simulator.trigger_anomaly(anomaly_type=a_type, duration_s=120)
            run_allocation()
            message = f"Jarvis: Emergency reroute initiated for {intent['condition']}. Live paths recalculating."
            
        elif intent["action"] == "hold":
            count = 0
            for sid, s in _shipments.items():
                if intent["priority"] == "All" or s["priority"] == intent["priority"]:
                    if s["status"] == "pending":
                        s["status"] = "held (storm alert)"
                        count += 1
            message = f"Jarvis: Action executed. {count} {intent['priority']} cargo holds applied."
            
        else:
            # allocate
            res = run_allocation()
            message = f"Jarvis: Auto-allocation complete. {res['allocated']} assigned."

        return {"message": message, "intent": intent}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")


@app.get("/api/manifests")
def list_manifests():
    """Return all generated dispatch manifests."""
    return {"manifests": get_manifests(), "total": len(get_manifests())}


# ══════════════════════════════════════════════════════════════════════
#  FLEET
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/fleet")
def fleet_status():
    """Return full fleet status and summary."""
    return fleet_manager.get_fleet_summary()

@app.post("/api/fleet/swarm")
def trigger_swarm():
    return fleet_manager.trigger_swarm_mode()


# ══════════════════════════════════════════════════════════════════════
#  REAL-TIME SIMULATION
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/realtime")
def get_realtime():
    """Get current real-time conditions snapshot."""
    return simulator.get_current_state()


@app.post("/api/simulate/trigger-anomaly")
def trigger_anomaly(req: AnomalyRequest):
    """Inject a simulated anomaly (traffic spike / severe weather / combined)."""
    simulator.trigger_anomaly(anomaly_type=req.anomaly_type, duration_s=req.duration_s)
    return {
        "message": f"Anomaly '{req.anomaly_type}' triggered for {req.duration_s}s.",
        "current_state": simulator.get_current_state(),
    }


@app.post("/api/simulate/resolve-anomaly")
def resolve_anomaly():
    """Manually resolve an active anomaly."""
    simulator.resolve_anomaly()
    return {"message": "Anomaly resolved.", "current_state": simulator.get_current_state()}


@app.get("/api/stream")
async def sse_stream():
    """
    Server-Sent Events stream — pushes real-time conditions every ~5 seconds.
    Subscribe from the frontend to get live traffic/weather updates.
    """
    q: queue.Queue = queue.Queue(maxsize=50)
    simulator.subscribe(q)

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: q.get(timeout=10)
                    )
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    # Heartbeat
                    yield f"data: {json.dumps({'heartbeat': True, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            simulator.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ══════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/analytics")
def analytics():
    """Return aggregated performance analytics from shipment history."""
    shipments = get_all_shipments()
    total = len(shipments)
    if total == 0:
        return {"message": "No data yet."}

    delivered  = [s for s in shipments if s["status"] == "delivered"]
    allocated  = [s for s in shipments if s["status"] == "allocated"]
    pending    = [s for s in shipments if s["status"] == "pending"]

    by_priority = {}
    for p in ["Critical", "High", "Medium", "Low"]:
        by_priority[p] = sum(1 for s in shipments if s["priority"] == p)

    by_cargo = {}
    for s in shipments:
        ct = s["cargo_type"]
        by_cargo[ct] = by_cargo.get(ct, 0) + 1

    return {
        "total_shipments": total,
        "delivered": len(delivered),
        "in_transit": len(allocated),
        "pending": len(pending),
        "on_time_rate_pct": round(len(delivered) / max(total, 1) * 100, 1),
        "by_priority": by_priority,
        "by_cargo_type": by_cargo,
        "fleet_summary": fleet_manager.get_fleet_summary(),
        "model_metrics": prediction_engine.get_model_metrics(),
        "realtime_conditions": simulator.get_current_state(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
