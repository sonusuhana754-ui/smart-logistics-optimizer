<<<<<<< HEAD
# hackv3
=======
# AI-Powered Intelligent Logistics Optimization System
# LogisticAI — README

## Quick Start

### 1. Install Python Backend Dependencies
```powershell
cd backend
pip install -r requirements.txt
```

### 2. Train ML Models (first run only, ~60 seconds)
```powershell
cd backend
python ml/train_models.py
```

### 3. Start the Backend API
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the Frontend (new terminal)
```powershell
cd frontend
npm run dev
```

### Or use the convenience script:
```powershell
.\start.ps1
```

---

## URLs
| Service     | URL                              |
|-------------|----------------------------------|
| Frontend    | http://localhost:5173            |
| Backend API | http://localhost:8000            |
| API Docs    | http://localhost:8000/docs       |

---

## System Modules

### 1. Prediction Engine (`backend/ml/`)
- **ETA Model**: XGBoost Regressor — predicts delivery duration in hours
- **Delay Model**: Random Forest Classifier — predicts delay probability (AUC-ROC scored)
- **Cost Model**: Gradient Boosting Regressor — estimates cost factor
- Trained on 10,000 synthetic supply chain records
- Real-time adjustment: multiplies ETA when traffic >70% or severe weather active

### 2. Route Optimization (`backend/routing/`)
- **Dijkstra**: Shortest distance paths
- **A\ * search**: Time-optimized routing with city-coordinate heuristic
- **VRP (Nearest Neighbor)**: Multi-stop delivery optimization
- Dynamic re-routing triggers when `delay_probability > 0.60`
- 20-city Indian road network graph with realistic edge weights

### 3. Shipment Automation (`backend/automation/`)
- Rule-based allocator: Priority (Critical > High > Medium > Low) sorted assignment
- Vehicle-cargo matching: Refrigerated trucks for Perishable, capacity-respecting
- APScheduler: Auto-runs allocation every 30 seconds
- Dispatch manifests auto-generated on allocation

### 4. Real-Time Simulation (`backend/data/realtime_simulator.py`)
- Background thread updates traffic + weather every 4 seconds
- Anomaly injection: `traffic_spike`, `severe_weather`, `combined`
- SSE stream at `/api/stream` for live frontend updates

---

## API Reference

| Method | Endpoint                          | Description                        |
|--------|-----------------------------------|------------------------------------|
| GET    | /api/health                       | System health check                |
| POST   | /api/predict                      | ETA + Delay + Cost prediction      |
| GET    | /api/predict/metrics              | ML model performance metrics       |
| POST   | /api/optimize-route               | Route optimization                 |
| POST   | /api/optimize-route/multi-stop    | Multi-stop VRP                     |
| GET    | /api/cities                       | Available city list + coordinates  |
| GET    | /api/shipments                    | List all shipments                 |
| POST   | /api/shipments                    | Add new shipment                   |
| POST   | /api/automate                     | Trigger auto-allocation            |
| GET    | /api/manifests                    | Dispatch manifests                 |
| GET    | /api/fleet                        | Fleet status                       |
| GET    | /api/realtime                     | Current RT conditions snapshot     |
| POST   | /api/simulate/trigger-anomaly     | Inject anomaly                     |
| POST   | /api/simulate/resolve-anomaly     | Resolve active anomaly             |
| GET    | /api/stream                       | SSE live stream                    |
| GET    | /api/analytics                    | Aggregated analytics               |
>>>>>>> c3706e7 (first commit)
