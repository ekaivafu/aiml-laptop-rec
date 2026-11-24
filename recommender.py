"""Laptop Recommender Engine.

Provides catalog loading, filtering, scoring, and nearest-neighbor ranking
for the Indian laptop catalog.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

# Required columns in the catalog dataset
REQUIRED_CATALOG_COLS = {
    "id",
    "brand",
    "model_name",
    "price_inr",
}

# Required columns in the feature dataset
REQUIRED_FEATURE_COLS = {
    "laptop_id",
    "score_confidence",
    "score_gaming",
    "score_aiml",
    "score_video_editing",
    "score_programming",
    "score_student_office",
    "score_portability",
    "score_value_for_money",
}

# Mapping from canonical use-case slugs to feature engineer score columns
USE_CASE_MAP = {
    "gaming": "score_gaming",
    "aiml": "score_aiml",
    "video-editing": "score_video_editing",
    "programming": "score_programming",
    "student-office": "score_student_office",
    "portability": "score_portability",
    "value": "score_value_for_money",
}

# Normalized aliases mapping user-friendly strings to canonical keys
USE_CASE_ALIASES = {
    "gaming": "gaming",
    "aiml": "aiml",
    "ai/ml": "aiml",
    "ai-ml": "aiml",
    "ai / ml": "aiml",
    "video-editing": "video-editing",
    "video editing": "video-editing",
    "programming": "programming",
    "coding": "programming",
    "student-office": "student-office",
    "student office": "student-office",
    "student / office": "student-office",
    "portability": "portability",
    "portable": "portability",
    "value": "value",
    "value for money": "value",
    "value-for-money": "value",
}


def canonicalize_use_case(use_case: str) -> str:
    """Normalize input use case string to a canonical key."""
    if not isinstance(use_case, str):
        raise ValueError(f"Use case must be a string, got {type(use_case)}")
    norm = use_case.strip().lower()
    if norm in USE_CASE_ALIASES:
        return USE_CASE_ALIASES[norm]
    if norm in USE_CASE_MAP:
        return norm
    raise ValueError(
        f"Invalid use case '{use_case}'. Must be one of: {list(USE_CASE_MAP.keys())}"
    )


def load_catalog(catalog_path: Path | str, features_path: Path | str) -> pd.DataFrame:
    """Load and join catalog and ML feature datasets.

    Enforces:
    - Stripping header whitespace.
    - Required column validation.
    - One-to-one join on laptops.csv.id = laptops_ml_ready.csv.laptop_id.
    - Surfacing unmatched IDs or duplicate keys as ValueError.
    - Scores are finite and within [0, 100].
    - Catalog values are preserved for prices, hardware, and shop links.
    """
    cat_path = Path(catalog_path)
    feat_path = Path(features_path)

    if not cat_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {cat_path}")
    if not feat_path.exists():
        raise FileNotFoundError(f"Features file not found: {feat_path}")

    # Read CSVs
    catalog_df = pd.read_csv(cat_path)
    features_df = pd.read_csv(feat_path)

    # Strip header whitespace
    catalog_df.columns = catalog_df.columns.astype(str).str.strip()
    features_df.columns = features_df.columns.astype(str).str.strip()

    # Validate required columns
    missing_cat_cols = REQUIRED_CATALOG_COLS - set(catalog_df.columns)
    if missing_cat_cols:
        raise ValueError(f"Catalog dataset missing required columns: {sorted(missing_cat_cols)}")

    missing_feat_cols = REQUIRED_FEATURE_COLS - set(features_df.columns)
    if missing_feat_cols:
        raise ValueError(f"Features dataset missing required columns: {sorted(missing_feat_cols)}")

    # Check for duplicate keys
    if catalog_df["id"].duplicated().any():
        dups = catalog_df["id"][catalog_df["id"].duplicated()].unique().tolist()
        raise ValueError(f"Duplicate id found in catalog data: {dups[:5]}")

    if features_df["laptop_id"].duplicated().any():
        dups = features_df["laptop_id"][features_df["laptop_id"].duplicated()].unique().tolist()
        raise ValueError(f"Duplicate laptop_id found in features data: {dups[:5]}")

    # Check for unmatched IDs (must be one-to-one)
    cat_ids = set(catalog_df["id"])
    feat_ids = set(features_df["laptop_id"])
    if cat_ids != feat_ids:
        missing_in_feat = cat_ids - feat_ids
        missing_in_cat = feat_ids - cat_ids
        err_msg = "Mismatch between catalog ids and features laptop_ids."
        if missing_in_feat:
            err_msg += f" IDs in catalog but not features: {list(missing_in_feat)[:5]}."
        if missing_in_cat:
            err_msg += f" IDs in features but not catalog: {list(missing_in_cat)[:5]}."
        raise ValueError(err_msg)

    # Validate feature score ranges [0, 100] and finiteness
    score_cols = [
        "score_gaming",
        "score_aiml",
        "score_video_editing",
        "score_programming",
        "score_student_office",
        "score_portability",
        "score_value_for_money",
    ]
    for col in score_cols:
        vals = pd.to_numeric(features_df[col], errors="coerce")
        if vals.isna().any() or not np.isfinite(vals).all():
            raise ValueError(f"Score column '{col}' contains non-finite or NaN values")
        if (vals < 0).any() or (vals > 100).any():
            raise ValueError(f"Score column '{col}' values must be within [0, 100]")

    # Validate score_confidence range [0, 1]
    conf_vals = pd.to_numeric(features_df["score_confidence"], errors="coerce")
    if conf_vals.isna().any() or not np.isfinite(conf_vals).all():
        raise ValueError("score_confidence contains non-finite or NaN values")
    if (conf_vals < 0).any() or (conf_vals > 1.0).any():
        raise ValueError("score_confidence values must be within [0, 1]")

    # Select feature columns to bring in (scores and score_confidence)
    # Avoid overwriting catalog values (price, hardware, shop links, etc.)
    bring_cols = ["laptop_id", "score_confidence"] + score_cols
    feat_subset = features_df[bring_cols]

    # One-to-one inner join
    merged = catalog_df.merge(
        feat_subset,
        left_on="id",
        right_on="laptop_id",
        how="inner",
    )

    if len(merged) != len(catalog_df):
        raise ValueError("Join failed to produce a strict one-to-one record mapping")

    return merged


def filter_catalog(
    catalog: pd.DataFrame,
    budget: int,
    *,
    brands: tuple[str, ...] = (),
    min_ram_gb: int | None = None,
    min_storage_gb: int | None = None,
) -> pd.DataFrame:
    """Filter catalog by hard budget cap and optional hardware criteria.

    Rules:
    - Budget must be positive; only finite positive catalog prices <= budget are kept.
    - Selected brands are alternatives within the brand filter (OR).
    - Active filters are combined with AND.
    - Observed RAM and storage are used for minimums.
    - A missing specification fails only when its corresponding filter is active.
    """
    if budget is None or not isinstance(budget, (int, float, np.integer, np.floating)):
        raise ValueError("Budget must be a positive number")
    if budget <= 0 or not np.isfinite(budget):
        raise ValueError("Budget must be a positive number")

    # Hard budget filter: finite, positive, <= budget
    prices = pd.to_numeric(catalog["price_inr"], errors="coerce")
    mask = prices.notna() & np.isfinite(prices) & (prices > 0) & (prices <= budget)

    # Brand filter (OR within selected brands, case-insensitive)
    cleaned_brands = [b.strip().lower() for b in brands if b and b.strip()]
    if cleaned_brands:
        brand_series = catalog["brand"].astype(str).str.strip().str.lower()
        brand_mask = brand_series.isin(cleaned_brands)
        mask = mask & brand_mask

    # RAM filter (active only if min_ram_gb is not None)
    if min_ram_gb is not None:
        if min_ram_gb <= 0:
            raise ValueError("min_ram_gb must be positive when specified")
        ram_vals = pd.to_numeric(catalog["ram_gb"], errors="coerce")
        ram_mask = ram_vals.notna() & np.isfinite(ram_vals) & (ram_vals >= min_ram_gb)
        mask = mask & ram_mask

    # Storage filter (active only if min_storage_gb is not None)
    if min_storage_gb is not None:
        if min_storage_gb <= 0:
            raise ValueError("min_storage_gb must be positive when specified")
        storage_vals = pd.to_numeric(catalog["storage_gb"], errors="coerce")
        storage_mask = storage_vals.notna() & np.isfinite(storage_vals) & (storage_vals >= min_storage_gb)
        mask = mask & storage_mask

    return catalog[mask].copy()


def recommend(
    eligible: pd.DataFrame,
    use_case: str,
    top: int = 5,
) -> pd.DataFrame:
    """Rank eligible laptops for a primary use case using nearest-neighbor search.

    Dimensions:
    - Standard use cases: Euclidean distance to scaled ideal (1, 1) on
      (use_case_score/100 * sqrt(0.8), value_score/100 * sqrt(0.2)).
    - 'value': Uses value_for_money score alone (ideal = 1.0).

    Tie-breaking:
    1. Distance ascending
    2. Confidence descending
    3. Catalog price ascending
    4. Numeric laptop_id ascending
    """
    if top <= 0:
        raise ValueError("top must be a positive integer")

    canon_use_case = canonicalize_use_case(use_case)

    if eligible.empty:
        return eligible.copy()

    df = eligible.copy()
    score_col = USE_CASE_MAP[canon_use_case]

    val_scores = pd.to_numeric(df["score_value_for_money"], errors="coerce").fillna(0.0).to_numpy()
    conf_scores = pd.to_numeric(df["score_confidence"], errors="coerce").fillna(0.0).to_numpy()
    prices = pd.to_numeric(df["price_inr"], errors="coerce").fillna(float("inf")).to_numpy()
    numeric_ids = pd.to_numeric(df["laptop_id"], errors="coerce").fillna(0).to_numpy()

    if canon_use_case == "value":
        # For value, use value score alone scaled to [0, 1], query ideal = 1.0
        v_scaled = (val_scores / 100.0).reshape(-1, 1)
        ideal = np.array([[1.0]])
        nn = NearestNeighbors(n_neighbors=len(df), metric="euclidean")
        nn.fit(v_scaled)
        distances = np.abs(1.0 - (val_scores / 100.0))
    else:
        # Standard 2D weighted Euclidean space
        u_scores = pd.to_numeric(df[score_col], errors="coerce").fillna(0.0).to_numpy()
        w_use = math.sqrt(0.8)
        w_val = math.sqrt(0.2)

        X = np.column_stack([
            (u_scores / 100.0) * w_use,
            (val_scores / 100.0) * w_val,
        ])
        ideal = np.array([[w_use, w_val]])
        nn = NearestNeighbors(n_neighbors=len(df), metric="euclidean")
        nn.fit(X)
        distances = np.linalg.norm(X - ideal, axis=1)

    df["__distance"] = distances
    df["__confidence"] = conf_scores
    df["__price"] = prices
    df["__num_id"] = numeric_ids

    # Sort: distance asc, confidence desc, price asc, numeric_id asc
    df = df.sort_values(
        by=["__distance", "__confidence", "__price", "__num_id"],
        ascending=[True, False, True, True],
    )

    df = df.drop(columns=["__distance", "__confidence", "__price", "__num_id"])
    return df.iloc[:top].copy()


def format_inr(amount: float | int | None) -> str:
    """Format numeric value into Indian currency notation (e.g. ₹79,990)."""
    if amount is None or pd.isna(amount):
        return "N/A"
    try:
        amt = int(round(float(amount)))
        s = str(amt)
        if len(s) <= 3:
            return f"₹{s}"
        last_three = s[-3:]
        rest = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        return f"₹{','.join(groups)},{last_three}"
    except Exception:
        return f"₹{amount}"


def format_specs_line(row: pd.Series | dict) -> str:
    """Format key hardware specifications into a clean dot-separated line."""
    cpu = row.get("cpu_model")
    if not cpu or pd.isna(cpu) or str(cpu).strip().lower() in ("nan", "none", ""):
        cpu = row.get("cpu_brand")
    if not cpu or pd.isna(cpu) or str(cpu).strip().lower() in ("nan", "none", ""):
        cpu = "Unknown CPU"

    gpu = row.get("gpu_model")
    if not gpu or pd.isna(gpu) or str(gpu).strip().lower() in ("nan", "none", ""):
        if bool(row.get("is_dedicated_gpu")):
            gpu = "Dedicated GPU"
        else:
            gpu = "Integrated Graphics"

    ram = row.get("ram_gb")
    if ram is not None and pd.notna(ram) and float(ram) > 0:
        ram_str = f"{int(float(ram))} GB RAM"
    else:
        ram_str = "Unknown RAM"

    storage = row.get("storage_gb")
    if storage is not None and pd.notna(storage) and float(storage) > 0:
        st_gb = int(float(storage))
        if st_gb >= 1024 and st_gb % 1024 == 0:
            st_str = f"{st_gb // 1024} TB SSD"
        else:
            st_str = f"{st_gb} GB SSD"
    else:
        st_str = "Unknown Storage"

    return f"{cpu} · {gpu} · {ram_str} · {st_str}"


def get_listing_url(shop_links: Any, best_store: str | None = None) -> str | None:
    """Extract a valid HTTP/HTTPS store URL from catalog shop_links."""
    if not shop_links or pd.isna(shop_links):
        return None

    if isinstance(shop_links, str):
        shop_links = shop_links.strip()
        if shop_links.startswith("http://") or shop_links.startswith("https://"):
            return shop_links
        try:
            parsed = json.loads(shop_links)
            if isinstance(parsed, dict):
                shop_links = parsed
        except Exception:
            return None

    if isinstance(shop_links, dict):
        if best_store and best_store.lower() in shop_links:
            url = shop_links[best_store.lower()]
            if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                return url
        for url in shop_links.values():
            if isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                return url

    return None


def generate_match_reason(row: pd.Series | dict, use_case: str) -> str:
    """Generate a short, clear reason tied to the use case and observed specs."""
    canon = canonicalize_use_case(use_case)
    gpu = str(row.get("gpu_model") or "").strip()
    is_dgpu = bool(row.get("is_dedicated_gpu"))
    ram = int(float(row.get("ram_gb"))) if pd.notna(row.get("ram_gb")) and float(row.get("ram_gb")) > 0 else None
    weight = round(float(row.get("weight_kg")), 2) if pd.notna(row.get("weight_kg")) and float(row.get("weight_kg")) > 0 else None
    cpu = str(row.get("cpu_model") or row.get("cpu_brand") or "processor").strip()

    ram_text = f"{ram} GB RAM" if ram else "balanced memory"

    if canon == "gaming":
        if is_dgpu and ram and ram >= 16:
            return f"Dedicated graphics and {ram} GB RAM suit your gaming needs."
        if is_dgpu:
            return f"Dedicated GPU delivers solid gaming performance and graphics acceleration."
        return f"Capable {cpu} and {ram_text} handle casual gaming and daily tasks."

    if canon == "student-office":
        if weight and weight <= 1.5:
            return f"Lightweight design ({weight} kg) with {ram_text} and responsive {cpu} for daily productivity."
        return f"Efficient {cpu} with {ram_text} ensures smooth multitasking and study sessions."

    if canon == "programming":
        if ram and ram >= 16:
            return f"Multi-core {cpu} with {ram} GB RAM provides fast compiling and development multitasking."
        return f"Solid {cpu} and {ram_text} deliver responsive coding and workflow execution."

    if canon == "video-editing":
        if is_dgpu:
            return f"Dedicated {gpu or 'graphics'} and {ram_text} provide rendering throughput for creative workflows."
        return f"Capable {cpu} and vibrant display handle content creation and editing tasks."

    if canon == "aiml":
        if is_dgpu:
            vram = row.get("gpu_vram_gb")
            vram_txt = f"{int(float(vram))} GB VRAM" if vram and pd.notna(vram) and float(vram) > 0 else "dedicated GPU"
            return f"Equipped with {vram_txt} and {ram_text} for local model inference and data science."
        return f"{cpu} with {ram_text} suitable for data manipulation, notebooks, and ML libraries."

    if canon == "portability":
        if weight:
            return f"Ultra-portable at {weight} kg with solid battery capacity for on-the-go mobility."
        return f"Compact build and efficient processor designed for active mobile work."

    # Value for money
    return f"Exceptional price-to-performance balance featuring {cpu} and {ram_text}."
