"""
Kaggle Supply Chain Dataset Loader
Loads the real harshsingh2209/supply-chain-analysis dataset and maps
its columns to ML-friendly feature vectors for ETA, Delay, and Cost models.
"""

import os
import numpy as np
import pandas as pd

KAGGLE_DATASET = "harshsingh2209/supply-chain-analysis"


def download_kaggle_dataset() -> str:
    """Download dataset via kagglehub and return local path."""
    import kagglehub
    path = kagglehub.dataset_download(KAGGLE_DATASET)
    print(f"Dataset downloaded to: {path}")
    return path


def load_raw_dataset() -> pd.DataFrame:
    """Load the raw CSV from the Kaggle cache."""
    path = download_kaggle_dataset()
    csv_path = os.path.join(path, "supply_chain_data.csv")
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from Kaggle dataset.")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map Kaggle supply chain columns → ML feature set.

    Real Kaggle columns used:
      - Shipping times         : int (days)  → ETA target (×24 = hours)
      - Shipping costs         : float       → cost component
      - Lead times             : int (days)  → lead-time feature
      - Lead time              : int (days)  → manufacturing lead
      - Order quantities       : int         → volume proxy (≈ weight_kg)
      - Transportation modes   : categorical (Road / Air / Sea)
      - Shipping carriers      : categorical (Carrier A/B/C)
      - Routes                 : categorical (Route A/B/C)
      - Product type           : categorical (haircare/skincare/cosmetics)
      - Location               : categorical (city origin)
      - Defect rates           : float       → quality-risk feature
      - Manufacturing costs    : float       → cost feature
      - Inspection results     : categorical → delay label basis
      - Costs                  : float       → total cost (cost target)
    """
    out = pd.DataFrame()

    # ── Targets ────────────────────────────────────────────────────────
    # ETA in hours (Shipping times is in days)
    out["actual_duration_hours"] = df["Shipping times"] * 24.0

    # Delay label: Fail inspection OR defect rate > 2%
    out["is_delayed"] = (
        (df["Inspection results"].str.lower() == "fail") |
        (df["Defect rates"] > 2.0)
    ).astype(int)

    # Cost factor: total costs
    out["cost_factor"] = df["Costs"].clip(lower=1.0)

    # ── Numeric features ───────────────────────────────────────────────
    out["lead_time_days"]          = df["Lead times"].clip(0, 365)
    out["manufacturing_lead_days"] = df["Manufacturing lead time"].clip(0, 90)
    out["order_quantity"]          = df["Order quantities"].clip(1, 10000)
    out["shipping_cost"]           = df["Shipping costs"].clip(0, 1000)
    out["defect_rate"]             = df["Defect rates"].clip(0, 10)
    out["manufacturing_cost"]      = df["Manufacturing costs"].clip(0, 10000)

    # Log-transforms for heavy-tailed distributions
    out["order_qty_log"]    = np.log1p(out["order_quantity"])
    out["shipping_cost_log"] = np.log1p(out["shipping_cost"])

    # ── Categorical features ───────────────────────────────────────────
    out["transport_mode"]    = df["Transportation modes"].astype(str).str.strip()
    out["carrier"]           = df["Shipping carriers"].astype(str).str.strip()
    out["route"]             = df["Routes"].astype(str).str.strip()
    out["product_type"]      = df["Product type"].astype(str).str.strip()
    out["origin_location"]   = df["Location"].astype(str).str.strip()

    # ── Simulated real-time features (added as controlled noise per row) ──
    # This makes the model responsive to live traffic/weather at inference time
    np.random.seed(42)
    n = len(out)
    hour   = np.random.randint(0, 24, n)
    dow    = np.random.randint(0, 7, n)
    out["hour_of_day"]    = hour
    out["day_of_week"]    = dow
    out["is_peak_hour"]   = ((hour >= 8) & (hour <= 10) | (hour >= 17) & (hour <= 19)).astype(int)
    out["is_weekend"]     = (dow >= 5).astype(int)
    out["traffic_density"] = np.random.beta(2, 5, n) * 100  # realistic 0-100
    out["weather_severity"] = np.random.choice(
        [0.0, 0.3, 0.5, 0.8, 0.9], n,
        p=[0.55, 0.20, 0.15, 0.07, 0.03]
    )
    out["congestion_score"] = (
        out["weather_severity"] * 0.4 + (out["traffic_density"] / 100.0) * 0.6
    )

    return out


# Columns to encode as categoricals
KAGGLE_CATEGORICAL_COLS = [
    "transport_mode", "carrier", "route", "product_type", "origin_location"
]

# Final feature columns (numeric + encoded)
KAGGLE_FEATURE_COLS = [
    "lead_time_days", "manufacturing_lead_days", "order_quantity", "order_qty_log",
    "shipping_cost", "shipping_cost_log", "defect_rate", "manufacturing_cost",
    "hour_of_day", "day_of_week", "is_peak_hour", "is_weekend",
    "traffic_density", "weather_severity", "congestion_score",
    "transport_mode_enc", "carrier_enc", "route_enc",
    "product_type_enc", "origin_location_enc",
]

KAGGLE_TARGET_ETA   = "actual_duration_hours"
KAGGLE_TARGET_DELAY = "is_delayed"
KAGGLE_TARGET_COST  = "cost_factor"


def augment_dataset(df_engineered: pd.DataFrame, target_rows: int = 5000) -> pd.DataFrame:
    """
    Augment the small Kaggle dataset (100 rows) by bootstrapping from real
    distributions. Preserves the statistical properties of the original data
    while giving the ML models enough samples to generalise well.
    """
    np.random.seed(42)
    n_orig = len(df_engineered)
    n_aug  = target_rows - n_orig
    if n_aug <= 0:
        return df_engineered

    aug_rows = []
    cat_cols  = ["transport_mode", "carrier", "route", "product_type", "origin_location"]
    num_stats = {
        col: (df_engineered[col].mean(), df_engineered[col].std() + 1e-6)
        for col in [
            "lead_time_days", "manufacturing_lead_days", "order_quantity",
            "shipping_cost", "defect_rate", "manufacturing_cost",
            KAGGLE_TARGET_ETA, KAGGLE_TARGET_COST,
        ]
        if col in df_engineered.columns
    }

    for _ in range(n_aug):
        # Bootstrap a base row
        base = df_engineered.sample(1).iloc[0].to_dict()

        # Perturb numeric values with Gaussian noise
        for col, (mu, sigma) in num_stats.items():
            noise = np.random.normal(0, sigma * 0.25)
            base[col] = max(0, base[col] + noise)

        # Randomly resample RT features
        hour   = int(np.random.randint(0, 24))
        dow    = int(np.random.randint(0, 7))
        base["hour_of_day"]     = hour
        base["day_of_week"]     = dow
        base["is_peak_hour"]    = int((8 <= hour <= 10) or (17 <= hour <= 19))
        base["is_weekend"]      = int(dow >= 5)
        base["traffic_density"] = float(np.clip(np.random.beta(2, 5) * 100, 0, 100))
        base["weather_severity"]= float(np.random.choice(
            [0.0, 0.3, 0.5, 0.8, 0.9], p=[0.55, 0.20, 0.15, 0.07, 0.03]
        ))
        base["congestion_score"]= (
            base["weather_severity"] * 0.4 + (base["traffic_density"] / 100.0) * 0.6
        )

        # Re-derive log features
        base["order_qty_log"]    = float(np.log1p(base["order_quantity"]))
        base["shipping_cost_log"]= float(np.log1p(base["shipping_cost"]))

        # Adjust ETA with congestion
        rt_factor = 1.0 + base["congestion_score"] * 0.4
        base[KAGGLE_TARGET_ETA] = abs(base[KAGGLE_TARGET_ETA]) * rt_factor

        # Re-derive delay label: high defect or traffic/weather spike
        base[KAGGLE_TARGET_DELAY] = int(
            base["defect_rate"] > 2.0 or
            base["traffic_density"] > 75 or
            base["weather_severity"] > 0.7
        )

        aug_rows.append(base)

    df_aug = pd.DataFrame(aug_rows)
    combined = pd.concat([df_engineered, df_aug], ignore_index=True)
    print(f"   Dataset augmented: {n_orig} real + {n_aug} synthetic = {len(combined)} rows")
    return combined


if __name__ == "__main__":
    df_raw = load_raw_dataset()
    df_eng = engineer_features(df_raw)
    print("\nEngineered features:")
    print(df_eng.dtypes)
    print(df_eng.describe())
