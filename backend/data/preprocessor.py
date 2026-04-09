"""
Data Preprocessor & Feature Engineer
Cleans the supply chain dataset and extracts ML-ready features.
"""

import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib


CATEGORICAL_COLS = ["cargo_type", "priority", "vehicle_type", "carrier", "weather_condition"]
FEATURE_COLS = [
    "distance_km", "weight_kg", "day_of_week", "hour_of_day",
    "is_peak_hour", "is_weekend", "weather_severity", "traffic_density",
    "cargo_type_enc", "priority_enc", "vehicle_type_enc",
    "carrier_enc", "weather_condition_enc",
    "weight_log", "distance_log", "congestion_score",
]

TARGET_ETA = "actual_duration_hours"
TARGET_DELAY = "is_delayed"
TARGET_COST = "cost_factor"


class DataPreprocessor:
    def __init__(self, models_dir: str = None):
        self.models_dir = models_dir or os.path.join(
            os.path.dirname(__file__), "..", "ml", "models"
        )
        self.encoders: dict[str, LabelEncoder] = {}
        self.scaler = StandardScaler()
        self._fitted = False

    # ── Public ────────────────────────────────────────────────────────

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean + engineer + encode + scale. Returns feature-ready dataframe."""
        df = self._clean(df)
        df = self._engineer(df)
        df = self._encode(df, fit=True)
        self._fitted = True
        self._save_encoders()
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform new data using fitted encoders."""
        if not self._fitted:
            self._load_encoders()
        df = self._clean(df)
        df = self._engineer(df)
        df = self._encode(df, fit=False)
        return df

    def get_feature_matrix(self, df: pd.DataFrame):
        """Return X (features) as numpy array."""
        available = [c for c in FEATURE_COLS if c in df.columns]
        return df[available].values

    # ── Private ───────────────────────────────────────────────────────

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Drop duplicates & nulls
        df = df.drop_duplicates(subset=["shipment_id"] if "shipment_id" in df.columns else None)
        df = df.dropna(subset=["distance_km", "weight_kg", "actual_duration_hours"]
                       if "actual_duration_hours" in df.columns else ["distance_km", "weight_kg"])

        # Clip outliers
        df["distance_km"] = df["distance_km"].clip(50, 5000)
        df["weight_kg"] = df["weight_kg"].clip(1, 25000)
        if "actual_duration_hours" in df.columns:
            df["actual_duration_hours"] = df["actual_duration_hours"].clip(0.5, 200)
        if "cost_factor" in df.columns:
            df["cost_factor"] = df["cost_factor"].clip(5, 5000)

        return df

    def _engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Log transforms for heavy-tailed features
        df["weight_log"] = np.log1p(df["weight_kg"])
        df["distance_log"] = np.log1p(df["distance_km"])

        # Combined congestion score
        ws = df["weather_severity"] if "weather_severity" in df.columns else 0
        td = df["traffic_density"] if "traffic_density" in df.columns else 30
        df["congestion_score"] = ws * 0.4 + (td / 100.0) * 0.6

        # Peak hours matrix
        if "hour_of_day" not in df.columns and "departure_datetime" in df.columns:
            df["hour_of_day"] = pd.to_datetime(df["departure_datetime"]).dt.hour
            df["day_of_week"] = pd.to_datetime(df["departure_datetime"]).dt.dayofweek
        if "is_peak_hour" not in df.columns:
            df["is_peak_hour"] = df["hour_of_day"].apply(
                lambda h: 1 if h in range(8, 11) or h in range(17, 20) else 0
            )
        if "is_weekend" not in df.columns:
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        return df

    def _encode(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        df = df.copy()
        for col in CATEGORICAL_COLS:
            if col not in df.columns:
                df[f"{col}_enc"] = 0
                continue
            enc_col = f"{col}_enc"
            if fit:
                le = LabelEncoder()
                df[enc_col] = le.fit_transform(df[col].astype(str))
                self.encoders[col] = le
            else:
                le = self.encoders.get(col)
                if le is None:
                    df[enc_col] = 0
                else:
                    # Handle unseen labels
                    known = set(le.classes_)
                    df[col] = df[col].apply(lambda x: x if x in known else le.classes_[0])
                    df[enc_col] = le.transform(df[col].astype(str))
        return df

    def _save_encoders(self):
        os.makedirs(self.models_dir, exist_ok=True)
        joblib.dump(self.encoders, os.path.join(self.models_dir, "encoders.pkl"))
        print("Encoders saved.")

    def _load_encoders(self):
        path = os.path.join(self.models_dir, "encoders.pkl")
        if os.path.exists(path):
            self.encoders = joblib.load(path)
            self._fitted = True
        else:
            raise FileNotFoundError("Encoders not found. Run train_models.py first.")
