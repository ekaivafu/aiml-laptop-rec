"""Unit tests for the trained supervised machine learning price model."""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from recommender import load_catalog

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "laptop_price_model.joblib"
CATALOG_PATH = BASE_DIR / "data" / "exports" / "laptops.csv"
FEATURES_PATH = BASE_DIR / "data" / "exports" / "laptops_ml_ready.csv"


def test_model_artifact_exists_and_loads():
    """Verify the trained model joblib artifact exists and has expected keys."""
    assert MODEL_PATH.exists(), f"Model artifact not found at {MODEL_PATH}"
    artifact = joblib.load(MODEL_PATH)
    assert isinstance(artifact, dict)
    assert "model" in artifact
    assert "num_cols" in artifact
    assert "cat_cols" in artifact
    assert artifact["test_r2"] > 0.75
    assert artifact["test_mae"] < 30000


def test_model_predicts_positive_prices():
    """Verify the trained model produces realistic price predictions on catalog laptops."""
    artifact = joblib.load(MODEL_PATH)
    pipeline = artifact["model"]
    num_cols = artifact["num_cols"]
    cat_cols = artifact["cat_cols"]

    df = load_catalog(CATALOG_PATH, FEATURES_PATH)
    sample = df.head(10).copy()

    for col in num_cols:
        sample[col] = pd.to_numeric(sample[col], errors="coerce")
        sample[col] = sample[col].fillna(sample[col].median() if not pd.isna(sample[col].median()) else 0)

    for col in cat_cols:
        sample[col] = sample[col].fillna("Unknown").astype(str)

    X_sample = sample[num_cols + cat_cols]
    log_preds = pipeline.predict(X_sample)
    preds = np.expm1(log_preds)

    assert len(preds) == 10
    for p in preds:
        assert np.isfinite(p)
        assert p > 15000  # realistic positive laptop price
        assert p < 1000000
