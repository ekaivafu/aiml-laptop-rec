"""Laptop Price Prediction - Supervised Machine Learning Model Training.

Trains and evaluates supervised regression models on real observed catalog laptops
to predict fair market value from hardware specifications.

Models trained and evaluated:
1. Dummy Median Baseline
2. Ridge Linear Regression
3. HistGradientBoosting Regressor
4. Random Forest Regressor (Best Model)

Saves the best trained pipeline to `models/laptop_price_model.joblib`.
"""

import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from recommender import load_catalog

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "data" / "exports" / "laptops.csv"
FEATURES_PATH = BASE_DIR / "data" / "exports" / "laptops_ml_ready.csv"
MODELS_DIR = BASE_DIR / "models"


def prepare_dataset():
    """Load catalog and prepare feature matrix X and target y."""
    df = load_catalog(CATALOG_PATH, FEATURES_PATH)
    # Strictly filter to positive real observed catalog prices
    real = df[df["price_inr"].notna() & (df["price_inr"] > 0)].copy()

    num_cols = [
        "cpu_cores",
        "cpu_threads",
        "cpu_max_clock_ghz",
        "is_high_perf_cpu",
        "is_dedicated_gpu",
        "gpu_vram_gb",
        "ram_gb",
        "storage_gb",
        "screen_size_in",
        "resolution_width",
        "resolution_height",
        "refresh_rate_hz",
        "brightness_nits",
        "weight_kg",
        "battery_wh",
    ]
    cat_cols = ["brand", "cpu_brand", "gpu_brand", "os"]

    for col in num_cols:
        real[col] = pd.to_numeric(real[col], errors="coerce")
        real[col] = real[col].fillna(real[col].median())

    for col in cat_cols:
        real[col] = real[col].fillna("Unknown").astype(str)

    X = real[num_cols + cat_cols].copy()
    y = real["price_inr"].copy()

    return X, y, num_cols, cat_cols


def train_and_evaluate():
    """Train multiple regression models and save the best model artifact."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    X, y, num_cols, cat_cols = prepare_dataset()

    print(f"Loaded {len(X)} catalog laptops with positive snapshot prices.")
    print(f"Features: {len(num_cols)} numerical + {len(cat_cols)} categorical.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), num_cols),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_cols,
            ),
        ]
    )

    # 1. Baseline Median
    med = y_train.median()
    y_pred_base = np.full_like(y_test, med)
    mae_base = mean_absolute_error(y_test, y_pred_base)
    r2_base = r2_score(y_test, y_pred_base)
    print(f"\n1. Baseline (Median):    MAE = INR {mae_base:,.0f} | R2 = {r2_base:.3f}")

    # 2. Ridge Regression
    ridge_pipe = Pipeline([("pre", preprocessor), ("ridge", Ridge(alpha=1.0))])
    ridge_pipe.fit(X_train, np.log1p(y_train))
    y_pred_ridge = np.expm1(ridge_pipe.predict(X_test))
    mae_ridge = mean_absolute_error(y_test, y_pred_ridge)
    r2_ridge = r2_score(y_test, y_pred_ridge)
    print(f"2. Ridge Regression:     MAE = INR {mae_ridge:,.0f} | R2 = {r2_ridge:.3f}")

    # 3. HistGradientBoostingRegressor
    hgb_pipe = Pipeline(
        [
            ("pre", preprocessor),
            (
                "hgb",
                HistGradientBoostingRegressor(
                    max_iter=150, learning_rate=0.08, random_state=42
                ),
            ),
        ]
    )
    hgb_pipe.fit(X_train, np.log1p(y_train))
    y_pred_hgb = np.expm1(hgb_pipe.predict(X_test))
    mae_hgb = mean_absolute_error(y_test, y_pred_hgb)
    r2_hgb = r2_score(y_test, y_pred_hgb)
    print(f"3. HistGradientBoosting: MAE = INR {mae_hgb:,.0f} | R2 = {r2_hgb:.3f}")

    # 4. Random Forest Regressor
    rf_pipe = Pipeline(
        [
            ("pre", preprocessor),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=200, max_depth=16, random_state=42, n_jobs=-1
                ),
            ),
        ]
    )
    rf_pipe.fit(X_train, np.log1p(y_train))
    y_pred_rf = np.expm1(rf_pipe.predict(X_test))
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    rmse_rf = root_mean_squared_error(y_test, y_pred_rf)
    r2_rf = r2_score(y_test, y_pred_rf)
    print(
        f"4. Random Forest:        MAE = INR {mae_rf:,.0f} | RMSE = INR {rmse_rf:,.0f} | R2 = {r2_rf:.3f}"
    )

    # 5-Fold Cross Validation on Best Model (Random Forest)
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = []
    for train_idx, val_idx in kf.split(X):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
        rf_pipe.fit(X_tr, np.log1p(y_tr))
        preds = np.expm1(rf_pipe.predict(X_val))
        cv_scores.append(r2_score(y_val, preds))

    mean_cv_r2 = np.mean(cv_scores)
    print(f"\n5-Fold CV Mean R2 (Random Forest): {mean_cv_r2:.3f} (+/- {np.std(cv_scores):.3f})")

    # Fit best model on entire observed dataset and save artifact
    print("\nFitting final model on full dataset...")
    rf_pipe.fit(X, np.log1p(y))

    model_path = MODELS_DIR / "laptop_price_model.joblib"
    joblib.dump(
        {
            "model": rf_pipe,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "test_mae": mae_rf,
            "test_r2": r2_rf,
            "cv_r2": mean_cv_r2,
        },
        model_path,
    )
    print(f"Saved trained model artifact to {model_path} ({os.path.getsize(model_path):,} bytes).")


if __name__ == "__main__":
    train_and_evaluate()
