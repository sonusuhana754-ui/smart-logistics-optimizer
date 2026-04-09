"""
ML Model Training Pipeline — Kaggle Dataset Edition
Uses the real harshsingh2209/supply-chain-analysis dataset.
Trains ETA, Delay, and Cost prediction models.
"""

import os
import sys
import json
import numpy as np
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.kaggle_loader import (
    load_raw_dataset, engineer_features, augment_dataset,
    KAGGLE_CATEGORICAL_COLS, KAGGLE_FEATURE_COLS,
    KAGGLE_TARGET_ETA, KAGGLE_TARGET_DELAY, KAGGLE_TARGET_COST,
)

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, roc_auc_score, classification_report

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor
    HAS_XGBOOST = False
    print("XGBoost not found, using GradientBoostingRegressor as fallback.")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def train_all():
    os.makedirs(MODELS_DIR, exist_ok=True)

    print("=" * 60)
    print("  AI LOGISTICS -- MODEL TRAINING (Kaggle Dataset)")
    print("=" * 60)

    # ── 1. Load real Kaggle data ───────────────────────────────────────
    print("\n[1/5] Loading Kaggle supply chain dataset...")
    df_raw = load_raw_dataset()
    print(f"   Raw rows: {len(df_raw)}")

    # ── 2. Engineer features ───────────────────────────────────────────
    print("\n[2/5] Engineering features from Kaggle schema...")
    df_eng = engineer_features(df_raw)
    print(f"   Real rows: {len(df_eng)}")

    print("\n[2b] Augmenting dataset to 5000 rows...")
    df = augment_dataset(df_eng, target_rows=5000)
    print(f"   Delay rate: {df[KAGGLE_TARGET_DELAY].mean()*100:.1f}%")

    # ── 3. Encode categoricals ─────────────────────────────────────────
    print("\n[3/5] Encoding categorical features...")
    encoders = {}
    for col in KAGGLE_CATEGORICAL_COLS:
        le = LabelEncoder()
        df[f"{col}_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
        print(f"   {col}: {list(le.classes_)}")

    joblib.dump(encoders, os.path.join(MODELS_DIR, "kaggle_encoders.pkl"))
    print("   Encoders saved.")

    # ── 4. Build feature matrix ────────────────────────────────────────
    available = [c for c in KAGGLE_FEATURE_COLS if c in df.columns]
    print(f"\n[4/5] Building feature matrix ({len(available)} features)...")
    X = df[available].values
    y_eta   = df[KAGGLE_TARGET_ETA].values
    y_delay = df[KAGGLE_TARGET_DELAY].values
    y_cost  = df[KAGGLE_TARGET_COST].values

    X_train, X_test, y_eta_train, y_eta_test = train_test_split(X, y_eta,   test_size=0.2, random_state=42)
    _,       _,      y_del_train, y_del_test  = train_test_split(X, y_delay, test_size=0.2, random_state=42)
    _,       _,      y_cos_train, y_cos_test  = train_test_split(X, y_cost,  test_size=0.2, random_state=42)

    metrics = {}

    # ── 5a. ETA Model (XGBoost) ────────────────────────────────────────
    print("\n[5a] Training ETA Model (XGBoost Regressor)...")
    if HAS_XGBOOST:
        eta_model = XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.07,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
            tree_method="hist", verbosity=0
        )
    else:
        eta_model = XGBRegressor(n_estimators=200, max_depth=5, random_state=42)

    eta_model.fit(X_train, y_eta_train)
    y_eta_pred = eta_model.predict(X_test)
    eta_mae = mean_absolute_error(y_eta_test, y_eta_pred)
    eta_r2  = r2_score(y_eta_test, y_eta_pred)
    print(f"   MAE: {eta_mae:.2f} hrs   R2: {eta_r2:.4f}")
    metrics["eta"] = {"mae_hours": round(eta_mae, 4), "r2": round(eta_r2, 4)}
    joblib.dump(eta_model, os.path.join(MODELS_DIR, "eta_model.pkl"))
    print("   ETA model saved.")

    # ── 5b. Delay Model (Random Forest) ────────────────────────────────
    print("\n[5b] Training Delay Model (Random Forest Classifier)...")
    delay_model = RandomForestClassifier(
        n_estimators=200, max_depth=10, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    delay_model.fit(X_train, y_del_train)
    y_del_pred = delay_model.predict(X_test)
    y_del_prob = delay_model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_del_test, y_del_prob)
    print(f"   AUC-ROC: {auc:.4f}")
    print(classification_report(y_del_test, y_del_pred, target_names=["On-Time", "Delayed"]))
    metrics["delay"] = {"auc_roc": round(auc, 4)}
    joblib.dump(delay_model, os.path.join(MODELS_DIR, "delay_model.pkl"))
    print("   Delay model saved.")

    # ── 5c. Cost Model (Gradient Boosting) ─────────────────────────────
    print("\n[5c] Training Cost Model (Gradient Boosting Regressor)...")
    cost_model = GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.08,
        subsample=0.8, random_state=42
    )
    cost_model.fit(X_train, y_cos_train)
    y_cos_pred = cost_model.predict(X_test)
    cost_mae = mean_absolute_error(y_cos_test, y_cos_pred)
    cost_r2  = r2_score(y_cos_test, y_cos_pred)
    print(f"   MAE: {cost_mae:.2f}   R2: {cost_r2:.4f}")
    metrics["cost"] = {"mae": round(cost_mae, 4), "r2": round(cost_r2, 4)}
    joblib.dump(cost_model, os.path.join(MODELS_DIR, "cost_model.pkl"))
    print("   Cost model saved.")

    # ── Save feature list & metrics ────────────────────────────────────
    joblib.dump(available, os.path.join(MODELS_DIR, "feature_cols.pkl"))
    with open(os.path.join(MODELS_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE -- all models saved to backend/ml/models/")
    print("=" * 60)
    return metrics


if __name__ == "__main__":
    train_all()
