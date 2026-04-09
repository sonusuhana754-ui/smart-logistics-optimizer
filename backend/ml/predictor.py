"""
Prediction Engine — Kaggle-trained Inference Module
"""

import os
import json
import numpy as np
import joblib
from datetime import datetime, timedelta
from typing import Optional

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

# Kaggle categorical columns
KAGGLE_CATEGORICAL_COLS = [
    "transport_mode", "carrier", "route", "product_type", "origin_location"
]


class PredictionEngine:
    _instance: Optional["PredictionEngine"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load_models(self):
        if self._loaded:
            return
        try:
            self.eta_model    = joblib.load(os.path.join(MODELS_DIR, "eta_model.pkl"))
            self.delay_model  = joblib.load(os.path.join(MODELS_DIR, "delay_model.pkl"))
            self.cost_model   = joblib.load(os.path.join(MODELS_DIR, "cost_model.pkl"))
            self.feature_cols = joblib.load(os.path.join(MODELS_DIR, "feature_cols.pkl"))
            self.encoders     = joblib.load(os.path.join(MODELS_DIR, "kaggle_encoders.pkl"))
            self._loaded = True
            print("Prediction engine loaded (Kaggle-trained models).")
        except FileNotFoundError:
            print("Models not found. Training now...")
            self._train_and_load()

    def _train_and_load(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from ml.train_models import train_all
        train_all()
        self._loaded = False
        self.load_models()

    def _encode_cat(self, col: str, val: str) -> int:
        le = self.encoders.get(col)
        if le is None:
            return 0
        known = set(le.classes_)
        val_clean = val if val in known else le.classes_[0]
        return int(le.transform([val_clean])[0])

    def predict(
        self,
        origin: str,
        destination: str,
        distance_km: float,
        cargo_type: str,
        priority: str,
        weight_kg: float,
        vehicle_type: str,
        carrier: str,
        departure_datetime: str,
        weather_condition: str,
        weather_severity: float,
        traffic_density: float,
    ) -> dict:
        if not self._loaded:
            self.load_models()

        try:
            departure_dt = datetime.fromisoformat(departure_datetime)
        except Exception:
            departure_dt = datetime.utcnow()

        hour_of_day = departure_dt.hour
        day_of_week = departure_dt.weekday()
        is_peak_hour = 1 if hour_of_day in range(8, 11) or hour_of_day in range(17, 20) else 0
        is_weekend   = 1 if day_of_week >= 5 else 0
        congestion   = weather_severity * 0.4 + (traffic_density / 100.0) * 0.6

        # Map UI inputs → Kaggle feature space
        # distance → order_quantity proxy
        order_qty_proxy = min(weight_kg, 9999)
        shipping_cost_proxy = distance_km * 0.018 * (1 + weather_severity)

        # Map vehicle_type → transportation mode
        mode_map = {
            "Van": "Road", "Truck": "Road", "Heavy Truck": "Road",
            "Refrigerated": "Road", "Flatbed": "Road",
            "Air": "Air", "Sea": "Sea",
        }
        transport_mode = mode_map.get(vehicle_type, "Road")

        # Map cargo_type → product_type
        product_map = {
            "Electronics": "skincare", "Perishable": "haircare",
            "General": "cosmetics", "Hazardous": "cosmetics",
            "Fragile": "skincare", "Bulk": "haircare",
        }
        product_type = product_map.get(cargo_type, "cosmetics")

        # Route proxy based on distance
        route_proxy = "Route A" if distance_km < 500 else ("Route B" if distance_km < 1500 else "Route C")

        feature_map = {
            "lead_time_days":          max(1, int(distance_km / 200)),
            "manufacturing_lead_days": 5,
            "order_quantity":          order_qty_proxy,
            "order_qty_log":           np.log1p(order_qty_proxy),
            "shipping_cost":           shipping_cost_proxy,
            "shipping_cost_log":       np.log1p(shipping_cost_proxy),
            "defect_rate":             0.5 + weather_severity * 2.0,
            "manufacturing_cost":      weight_kg * 0.1,
            "hour_of_day":             hour_of_day,
            "day_of_week":             day_of_week,
            "is_peak_hour":            is_peak_hour,
            "is_weekend":              is_weekend,
            "traffic_density":         traffic_density,
            "weather_severity":        weather_severity,
            "congestion_score":        congestion,
            "transport_mode_enc":      self._encode_cat("transport_mode", transport_mode),
            "carrier_enc":             self._encode_cat("carrier", carrier),
            "route_enc":               self._encode_cat("route", route_proxy),
            "product_type_enc":        self._encode_cat("product_type", product_type),
            "origin_location_enc":     self._encode_cat("origin_location", origin),
        }

        X = np.array([[feature_map.get(c, 0.0) for c in self.feature_cols]])

        eta_hours   = float(self.eta_model.predict(X)[0])
        delay_prob  = float(self.delay_model.predict_proba(X)[0][1])
        cost_factor = float(self.cost_model.predict(X)[0])

        # Real-time boost
        rt_multiplier = 1.0
        if weather_severity > 0.6:
            rt_multiplier += weather_severity * 0.25
        if traffic_density > 70:
            rt_multiplier += (traffic_density - 70) / 100 * 0.20

        eta_hours_adj = eta_hours * rt_multiplier
        arrival_dt    = departure_dt + timedelta(hours=eta_hours_adj)

        risk_level = (
            "Critical" if delay_prob >= 0.75 else
            "High"     if delay_prob >= 0.55 else
            "Medium"   if delay_prob >= 0.25 else "Low"
        )

        return {
            "predicted_eta":          arrival_dt.isoformat(),
            "eta_hours":              round(eta_hours_adj, 2),
            "delay_probability":      round(delay_prob * 100, 1),
            "delay_risk_level":       risk_level,
            "cost_factor":            round(max(cost_factor, 5.0), 2),
            "rt_adjustment_applied":  rt_multiplier > 1.0,
            "rt_multiplier":          round(rt_multiplier, 3),
            "departure_datetime":     departure_dt.isoformat(),
            "inputs": {
                "origin": origin, "destination": destination,
                "distance_km": distance_km, "cargo_type": cargo_type,
                "priority": priority, "weight_kg": weight_kg,
                "weather_condition": weather_condition,
                "weather_severity": weather_severity,
                "traffic_density": traffic_density,
            },
        }

    def get_model_metrics(self) -> dict:
        path = os.path.join(MODELS_DIR, "metrics.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}


prediction_engine = PredictionEngine()
