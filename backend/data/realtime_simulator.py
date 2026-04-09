"""
Real-Time Data Simulator
Simulates live traffic density and weather conditions as streaming data.
Supports anomaly injection for dynamic re-routing demonstrations.
"""

import random
import time
import threading
from datetime import datetime
from typing import Optional

import numpy as np


class RealtimeSimulator:
    """Thread-safe real-time conditions simulator."""

    WEATHER_OPTIONS = ["Clear", "Rain", "Fog", "Storm", "Snow"]
    WEATHER_SEVERITY = {
        "Clear": 0.0, "Rain": 0.3, "Fog": 0.5, "Storm": 0.8, "Snow": 0.9
    }

    def __init__(self, update_interval_s: float = 5.0):
        self.update_interval_s = update_interval_s
        self._lock = threading.Lock()
        self._anomaly_active = False
        self._anomaly_expires_at: Optional[float] = None

        # Initial state
        self._state = {
            "traffic_density": 35.0,
            "weather_condition": "Clear",
            "weather_severity": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly_active": False,
            "anomaly_type": None,
        }

        # Subscribers: list of queues that receive updates
        self._subscribers: list = []

        # Noise model
        self._traffic_target = 35.0
        self._weather_index = 0

        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Public API ─────────────────────────────────────────────────────

    def start(self):
        """Start background simulation thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def get_current_state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def trigger_anomaly(self, anomaly_type: str = "traffic_spike", duration_s: float = 60.0):
        """
        Inject a real-time anomaly:
          - 'traffic_spike': traffic jumps to 85-95
          - 'severe_weather': weather shifts to Storm or Snow
          - 'combined': both traffic spike + severe weather
        """
        with self._lock:
            self._anomaly_active = True
            self._anomaly_expires_at = time.monotonic() + duration_s
            self._state["anomaly_active"] = True
            self._state["anomaly_type"] = anomaly_type

            if anomaly_type in ("traffic_spike", "combined"):
                self._traffic_target = random.uniform(82, 96)

            if anomaly_type in ("severe_weather", "combined"):
                severe = random.choice(["Storm", "Snow"])
                self._state["weather_condition"] = severe
                self._state["weather_severity"] = self.WEATHER_SEVERITY[severe]

        print(f"⚡ Anomaly triggered: {anomaly_type} for {duration_s}s")

    def resolve_anomaly(self):
        """Manually resolve an active anomaly."""
        with self._lock:
            self._anomaly_active = False
            self._anomaly_expires_at = None
            self._traffic_target = random.uniform(25, 55)
            self._state["anomaly_active"] = False
            self._state["anomaly_type"] = None

    def subscribe(self, queue):
        """Add a subscriber queue to receive SSE updates."""
        self._subscribers.append(queue)

    def unsubscribe(self, queue):
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass

    # ── Internal simulation loop ───────────────────────────────────────

    def _loop(self):
        while self._running:
            self._tick()
            time.sleep(self.update_interval_s)

    def _tick(self):
        with self._lock:
            # Check if anomaly has expired
            if self._anomaly_active and self._anomaly_expires_at:
                if time.monotonic() > self._anomaly_expires_at:
                    self._anomaly_active = False
                    self._anomaly_expires_at = None
                    self._traffic_target = random.uniform(25, 55)
                    self._state["anomaly_active"] = False
                    self._state["anomaly_type"] = None

            # ── Traffic random walk toward target ──────────────────────
            current_traffic = self._state["traffic_density"]
            noise = np.random.normal(0, 3)
            drift = (self._traffic_target - current_traffic) * 0.15
            new_traffic = float(np.clip(current_traffic + drift + noise, 0, 100))
            self._state["traffic_density"] = round(new_traffic, 2)

            # Occasionally update target
            if random.random() < 0.2 and not self._anomaly_active:
                hour = datetime.utcnow().hour
                base = 60 if 8 <= hour <= 10 or 17 <= hour <= 19 else 30
                self._traffic_target = base + random.uniform(-15, 15)

            # ── Weather slow drift ─────────────────────────────────────
            if not self._anomaly_active and random.random() < 0.05:
                new_weather = random.choice(self.WEATHER_OPTIONS)
                self._state["weather_condition"] = new_weather
                self._state["weather_severity"] = self.WEATHER_SEVERITY[new_weather]

            self._state["timestamp"] = datetime.utcnow().isoformat()

        # Notify subscribers (outside lock to avoid deadlock)
        state_copy = dict(self._state)
        for q in list(self._subscribers):
            try:
                q.put_nowait(state_copy)
            except Exception:
                pass


# ── Module-level singleton ─────────────────────────────────────────────
simulator = RealtimeSimulator(update_interval_s=4.0)
