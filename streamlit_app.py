"""Laptop Finder - Catalog Filtering & Recommendation Application.

A clean, minimalist, flat-designed interface with:
- Direct access to search (no landing page)
- Zero pill-shaped components (clean rectangular design)
- Zero emojis or pointers
- Zero gradients (flat solid architectural color palette)
- Unhyped, precise technical information
"""

from __future__ import annotations

import base64
from functools import lru_cache
import os
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from recommender import (
    load_catalog,
    filter_catalog,
    recommend,
    format_inr,
    format_specs_line,
    get_listing_url,
    generate_match_reason,
)

# Page configuration
st.set_page_config(
    page_title="Laptop Finder - Indian Laptop Catalog",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# File paths
BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "data" / "exports" / "laptops.csv"
FEATURES_PATH = BASE_DIR / "data" / "exports" / "laptops_ml_ready.csv"
IMAGE_CACHE_DIR = BASE_DIR / "data" / "cache" / "images"
MODEL_PATH = BASE_DIR / "models" / "laptop_price_model.joblib"


@st.cache_resource
def get_trained_price_model() -> dict | None:
    """Load serialized supervised Random Forest price prediction pipeline."""
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def estimate_fair_price(model_artifact: dict | None, row: pd.Series) -> int | None:
    """Predict fair market price in INR using the trained Random Forest model."""
    if not model_artifact:
        return None
    try:
        import numpy as np
        pipeline = model_artifact["model"]
        num_cols = model_artifact["num_cols"]
        cat_cols = model_artifact["cat_cols"]

        data = {}
        for c in num_cols:
            val = pd.to_numeric(row.get(c), errors="coerce")
            data[c] = [val if pd.notna(val) else 0.0]
        for c in cat_cols:
            val = row.get(c)
            data[c] = [str(val) if (val is not None and pd.notna(val)) else "Unknown"]

        df_single = pd.DataFrame(data)
        log_pred = pipeline.predict(df_single)
        fair_price = float(np.expm1(log_pred[0]))
        return int(round(fair_price)) if fair_price > 0 else None
    except Exception:
        return None

# Predefined options
BUDGET_OPTIONS = [
    "₹30,000",
    "₹40,000",
    "₹50,000",
    "₹60,000",
    "₹70,000",
    "₹80,000",
    "₹90,000",
    "₹1,00,000",
    "₹1,20,000",
    "₹1,50,000",
    "₹2,00,000",
    "₹2,50,000",
    "₹3,00,000",
]

USE_CASE_OPTIONS = [
    "Gaming",
    "Student / Office",
    "Programming",
    "Video Editing",
    "AI / ML",
    "Portability",
    "Value for Money",
]

RAM_OPTIONS = ["Any RAM", "8 GB", "16 GB", "24 GB", "32 GB"]
STORAGE_OPTIONS = ["Any storage", "256 GB", "512 GB", "1 TB (1024 GB)", "2 TB (2048 GB)"]


# Minimalist, flat, modern CSS (No gradients, no pill shapes, no emojis/pointers)
FLAT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-page: #f8fafc;
    --bg-card: #ffffff;
    --border: #e2e8f0;
    --border-strong: #cbd5e1;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    --text-muted: #64748b;
    --target-size: 38px;
}

@media (pointer: coarse) {
    :root {
        --target-size: 44px;
    }
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    color: var(--text-primary) !important;
    overflow-wrap: break-word;
}

.stApp {
    background-color: var(--bg-page) !important;
}

#MainMenu, footer, header, div[data-testid="stToolbar"] {
    display: none !important;
    visibility: hidden !important;
}

.block-container {
    max-width: 1080px !important;
    padding-top: clamp(1rem, 2.5vw, 2.5rem) !important;
    padding-bottom: clamp(2rem, 5vw, 4rem) !important;
    padding-left: max(1rem, env(safe-area-inset-left, 0px)) !important;
    padding-right: max(1rem, env(safe-area-inset-right, 0px)) !important;
}

/* Clean Navigation */
.top-nav {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-bottom: 1rem;
    margin-bottom: 1.75rem;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    gap: 0.5rem;
}
.site-title {
    font-size: clamp(1.2rem, 1rem + 1vw, 1.45rem);
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}
.site-meta {
    font-size: clamp(0.78rem, 0.72rem + 0.3vw, 0.85rem);
    color: var(--text-muted);
    font-weight: 500;
}

/* Headings */
.page-heading {
    font-size: clamp(1.4rem, 1.1rem + 1.5vw, 1.85rem) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.4rem !important;
    text-wrap: balance !important;
}
.page-subheading {
    font-size: clamp(0.88rem, 0.82rem + 0.3vw, 0.95rem) !important;
    color: var(--text-secondary) !important;
    line-height: 1.5 !important;
    margin-bottom: 1.75rem !important;
    text-wrap: pretty !important;
}

/* Buttons */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #0f172a !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.55rem 1.4rem !important;
    min-height: var(--target-size) !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease !important;
}
button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
    background-color: #1e293b !important;
    border-color: #1e293b !important;
}

button[kind="secondary"], .stButton > button[kind="secondary"], .stButton > button {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    min-height: var(--target-size) !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}
button[kind="secondary"]:hover, .stButton > button:hover {
    background-color: #f1f5f9 !important;
    border-color: #94a3b8 !important;
}

/* Form Container */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    padding: clamp(1rem, 2vw + 0.5rem, 1.75rem) !important;
}

div[data-testid="stSelectbox"] label p {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: var(--text-primary) !important;
}

/* Rectangular Filter Summary */
.summary-bar {
    background-color: #f1f5f9;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.6rem 0.85rem;
    font-size: clamp(0.82rem, 0.75rem + 0.3vw, 0.9rem);
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
    overflow-wrap: break-word;
    line-height: 1.5;
}

/* Best Match Card */
.best-card {
    background-color: #ffffff;
    border: 2px solid #0f172a;
    border-radius: 6px;
    padding: clamp(1.25rem, 2vw + 0.5rem, 2rem);
    margin-bottom: 2rem;
}
.best-card-content {
    display: flex;
    gap: 2rem;
    align-items: center;
}
.best-card-info {
    flex: 1;
    min-width: 0;
}
.best-card-media {
    flex-shrink: 0;
    width: 240px;
    height: 190px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #ffffff;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.75rem;
}
.best-card-img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    aspect-ratio: 4 / 3;
}
@media (max-width: 768px) {
    .best-card-content {
        flex-direction: column-reverse;
        align-items: stretch;
        gap: 1.25rem;
    }
    .best-card-media {
        width: 100% !important;
        max-width: 320px;
        height: 190px !important;
        margin: 0 auto;
    }
    .action-link {
        width: 100% !important;
        text-align: center !important;
    }
}
.badge-label {
    display: inline-block;
    background-color: #0f172a;
    color: #ffffff;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.6rem;
    border-radius: 3px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 0.85rem;
}
.laptop-title {
    font-size: clamp(1.25rem, 1rem + 1vw, 1.65rem) !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    line-height: 1.3 !important;
    margin-bottom: 0.4rem !important;
    text-wrap: balance !important;
}
.price-display {
    font-size: clamp(1.35rem, 1.1rem + 0.8vw, 1.55rem) !important;
    font-weight: 700 !important;
    color: #0f172a !important;
    margin-bottom: 0.35rem !important;
}
.fair-price-tag {
    font-size: 0.85rem;
    font-weight: 600;
    color: #334155;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 0.3rem 0.65rem;
    display: inline-block;
    margin-bottom: 0.85rem;
}
.fair-price-tag .deal-note {
    font-weight: 500;
    color: #0284c7;
}
.alt-fair-price {
    font-size: 0.78rem;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 3px;
    padding: 0.15rem 0.4rem;
    display: inline-block;
    margin-top: 0.15rem;
    margin-bottom: 0.5rem;
}
.specs-row {
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(0.75rem, 0.7rem + 0.3vw, 0.85rem);
    color: var(--text-secondary);
    background-color: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.6rem 0.85rem;
    margin-bottom: 1rem;
    overflow-wrap: anywhere;
    line-height: 1.5;
}
.reason-box {
    font-size: clamp(0.88rem, 0.82rem + 0.3vw, 0.95rem);
    color: var(--text-secondary);
    line-height: 1.5;
    margin-bottom: 1.25rem;
    text-wrap: pretty;
}

.action-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background-color: #0f172a;
    color: #ffffff !important;
    text-decoration: none !important;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.55rem 1.2rem;
    min-height: var(--target-size);
    border-radius: 4px;
    transition: background-color 0.15s ease;
}
.action-link:hover {
    background-color: #334155;
}

/* Alternatives Grid */
.alt-item {
    background-color: #ffffff;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: clamp(1.1rem, 1.5vw + 0.3rem, 1.5rem);
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    content-visibility: auto;
    contain-intrinsic-size: auto 380px;
}
.alt-media {
    width: 100%;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #ffffff;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.5rem;
    margin-bottom: 1rem;
}
.alt-img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    aspect-ratio: 4 / 3;
}
.alt-rank {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.4rem;
}
.alt-title {
    font-size: clamp(1.02rem, 0.95rem + 0.35vw, 1.18rem) !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.35rem !important;
    line-height: 1.35 !important;
    text-wrap: balance !important;
}
.alt-price {
    font-size: clamp(1.15rem, 1.05rem + 0.5vw, 1.28rem) !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.6rem !important;
}
.alt-specs {
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(0.72rem, 0.68rem + 0.25vw, 0.8rem);
    color: var(--text-muted);
    margin-bottom: 0.75rem;
    line-height: 1.45;
    overflow-wrap: anywhere;
}
.alt-reason {
    font-size: clamp(0.82rem, 0.78rem + 0.25vw, 0.88rem);
    color: var(--text-secondary);
    line-height: 1.45;
    margin-bottom: 1.25rem;
    flex: 1;
    text-wrap: pretty;
}
.alt-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background-color: transparent;
    color: #0f172a !important;
    text-decoration: none !important;
    font-weight: 600;
    font-size: 0.85rem;
    border: 1px solid var(--border-strong);
    padding: 0.45rem 0.95rem;
    min-height: var(--target-size);
    border-radius: 4px;
    align-self: flex-start;
    transition: all 0.15s ease;
}
.alt-link:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}
@media (max-width: 640px) {
    .alt-link {
        width: 100% !important;
        text-align: center !important;
    }
}

/* Footer */
.simple-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid var(--border);
    padding-top: 1.5rem;
    margin-top: 3.5rem;
    font-size: clamp(0.75rem, 0.7rem + 0.25vw, 0.85rem);
    color: var(--text-muted);
    flex-wrap: wrap;
    gap: 0.75rem;
}
</style>
"""


def clean_html(s: str) -> str:
    """Strip leading whitespace from each line so Markdown never parses it as code."""
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


@lru_cache(maxsize=512)
def get_base64_image(image_path: str) -> str | None:
    """Read and base64-encode a local image file with in-memory caching for zero-latency render."""
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:image/webp;base64,{encoded}"
    except Exception:
        return None


def render_product_image_html(
    image_url: Any,
    laptop_id: Any,
    model_name: str,
    css_class: str,
    is_hero: bool = False,
) -> str:
    """Render an HTML img tag with instant local base64 caching and clean fallback."""
    fallback_svg = (
        "data:image/svg+xml;utf8,"
        "%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='%2394a3b8'%20stroke-width='1.5'%20stroke-linecap='round'%20stroke-linejoin='round'%3E"
        "%3Crect%20x='3'%20y='4'%20width='18'%20height='12'%20rx='2'/%3E"
        "%3Cline%20x1='2'%20y1='20'%20x2='22'%20y2='20'/%3E"
        "%3C/svg%3E"
    )

    src = None
    if laptop_id and pd.notna(laptop_id):
        try:
            cached_file = IMAGE_CACHE_DIR / f"{int(float(laptop_id))}.webp"
            if cached_file.exists() and cached_file.stat().st_size > 500:
                src = get_base64_image(str(cached_file))
        except Exception:
            src = None

    if not src:
        if image_url and not pd.isna(image_url) and str(image_url).strip().startswith("http"):
            # Use optimized dimensions -w400-h400 instead of 1200x1200 to reduce size by ~80%
            src = str(image_url).strip().replace("-w1200-h1200", "-w400-h400")
        else:
            src = fallback_svg

    safe_name = str(model_name).replace('"', '&quot;').replace("'", "&#39;")
    fetch_priority = "high" if is_hero else "auto"

    return (
        f'<img src="{src}" alt="{safe_name}" class="{css_class}" '
        f'referrerpolicy="no-referrer" loading="eager" fetchpriority="{fetch_priority}" decoding="async" '
        f'onerror="this.onerror=null; this.src=\'{fallback_svg}\';" />'
    )


def parse_budget_inr(val: str | int | float) -> int:
    """Extract integer budget from formatted INR string or number."""
    if isinstance(val, (int, float)):
        return int(val)
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else 90000


def parse_ram_gb(val: str | int | None) -> int | None:
    """Extract integer RAM capacity from selection string."""
    if not val or val == "Any RAM" or str(val).strip().lower() in ("any", "none", ""):
        return None
    digits = re.sub(r"[^\d]", "", str(val))
    return int(digits) if digits else None


def parse_storage_gb(val: str | int | None) -> int | None:
    """Extract integer storage capacity from selection string."""
    if not val or val == "Any storage" or str(val).strip().lower() in ("any", "none", ""):
        return None
    s = str(val).lower()
    if "tb" in s:
        digits = re.sub(r"[^\d]", "", s.split("tb")[0])
        return int(digits) * 1024 if digits else 1024
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def make_filter_summary(
    use_case: str,
    budget: int,
    brand: str,
    min_ram: int | None,
    min_storage: int | None,
) -> str:
    """Format filter summary string without emojis or pointers."""
    parts = [use_case, f"Budget: Up to {format_inr(budget)}"]
    if brand and brand != "Any brand":
        parts.append(f"Brand: {brand}")
    if min_ram:
        parts.append(f"RAM: {min_ram} GB")
    if min_storage:
        if min_storage >= 1024 and min_storage % 1024 == 0:
            parts.append(f"Storage: {min_storage // 1024} TB")
        else:
            parts.append(f"Storage: {min_storage} GB")
    return " | ".join(parts)


@st.cache_data
def get_catalog_data():
    """Load catalog and feature datasets with caching."""
    if not CATALOG_PATH.exists() or not FEATURES_PATH.exists():
        return None
    try:
        return load_catalog(CATALOG_PATH, FEATURES_PATH)
    except Exception:
        return None


def render_navbar():
    """Render top title bar."""
    st.markdown(
        clean_html(
            """
            <div class="top-nav">
                <div class="site-title">Laptop Finder</div>
                <div class="site-meta">Indian Laptop Catalog (744 Models)</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def render_footer():
    """Render minimal footer."""
    st.markdown(
        clean_html(
            """
            <div class="simple-footer">
                <div>Laptop Finder - Catalog Ranking Engine</div>
                <div>Snapshot prices subject to retail change</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def init_session_state(brands: list[str]):
    """Initialize default session state directly on search form."""
    if "screen" not in st.session_state:
        st.session_state.screen = "preferences"
    if "budget" not in st.session_state:
        st.session_state.budget = "₹90,000"
    if "primary_use" not in st.session_state:
        st.session_state.primary_use = "Gaming"
    if "brand" not in st.session_state:
        st.session_state.brand = "Any brand"
    if "min_ram" not in st.session_state:
        st.session_state.min_ram = "16 GB"
    if "min_storage" not in st.session_state:
        st.session_state.min_storage = "512 GB"
    if "search_executed" not in st.session_state:
        st.session_state.search_executed = False


def main():
    st.markdown(FLAT_CSS, unsafe_allow_html=True)

    catalog_df = get_catalog_data()
    if catalog_df is None:
        render_navbar()
        st.error(
            "Catalog exports not found or invalid. "
            "Please run `python scraper.py export` from the project root to generate the required catalog CSVs."
        )
        render_footer()
        st.stop()

    unique_brands = sorted(
        [
            str(b).strip()
            for b in catalog_df["brand"].dropna().unique()
            if str(b).strip() and str(b).strip() != "Unknown"
        ]
    )
    brand_options = ["Any brand"] + unique_brands

    init_session_state(unique_brands)

    # =========================================================================
    # SCREEN 1: PREFERENCES / SEARCH (DIRECT ENTRY, NO LANDING PAGE)
    # =========================================================================
    if st.session_state.screen in ("preferences", "landing"):
        render_navbar()

        st.markdown(
            clean_html(
                """
                <div class="page-heading">Search and Filter Laptops</div>
                <div class="page-subheading">
                    Set your maximum budget in INR and primary use case. 
                    Hardware filters are optional and narrow the eligible set.
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            r1_col1, r1_col2 = st.columns(2, gap="large")
            with r1_col1:
                budget_idx = (
                    BUDGET_OPTIONS.index(st.session_state.budget)
                    if st.session_state.budget in BUDGET_OPTIONS
                    else 6
                )
                selected_budget = st.selectbox(
                    "Maximum budget",
                    options=BUDGET_OPTIONS,
                    index=budget_idx,
                    key="pref_budget",
                )
            with r1_col2:
                use_idx = (
                    USE_CASE_OPTIONS.index(st.session_state.primary_use)
                    if st.session_state.primary_use in USE_CASE_OPTIONS
                    else 0
                )
                selected_use = st.selectbox(
                    "Primary use",
                    options=USE_CASE_OPTIONS,
                    index=use_idx,
                    key="pref_use_case",
                )

            st.markdown("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.5rem 0;'>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #0f172a; margin-bottom: 1rem;'>Hardware Filters (Optional)</div>", unsafe_allow_html=True)

            r2_col1, r2_col2, r2_col3 = st.columns(3, gap="medium")
            with r2_col1:
                brand_idx = (
                    brand_options.index(st.session_state.brand)
                    if st.session_state.brand in brand_options
                    else 0
                )
                selected_brand = st.selectbox(
                    "Brand",
                    options=brand_options,
                    index=brand_idx,
                    key="pref_brand",
                )
            with r2_col2:
                ram_idx = (
                    RAM_OPTIONS.index(st.session_state.min_ram)
                    if st.session_state.min_ram in RAM_OPTIONS
                    else 2
                )
                selected_ram = st.selectbox(
                    "Minimum RAM",
                    options=RAM_OPTIONS,
                    index=ram_idx,
                    key="pref_min_ram",
                )
            with r2_col3:
                storage_idx = (
                    STORAGE_OPTIONS.index(st.session_state.min_storage)
                    if st.session_state.min_storage in STORAGE_OPTIONS
                    else 2
                )
                selected_storage = st.selectbox(
                    "Minimum storage",
                    options=STORAGE_OPTIONS,
                    index=storage_idx,
                    key="pref_min_storage",
                )

            st.markdown("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1.5rem 0;'>", unsafe_allow_html=True)

            _, btn_col2 = st.columns([0.7, 0.3])
            with btn_col2:
                if st.button("Find laptops", type="primary", use_container_width=True, key="btn_find_laptops"):
                    st.session_state.budget = selected_budget
                    st.session_state.primary_use = selected_use
                    st.session_state.brand = selected_brand
                    st.session_state.min_ram = selected_ram
                    st.session_state.min_storage = selected_storage
                    st.session_state.screen = "matching"
                    st.rerun()

        render_footer()

    # =========================================================================
    # SCREEN 2: MATCHING
    # =========================================================================
    elif st.session_state.screen == "matching":
        render_navbar()

        budget_int = parse_budget_inr(st.session_state.budget)
        ram_int = parse_ram_gb(st.session_state.min_ram)
        storage_int = parse_storage_gb(st.session_state.min_storage)
        brand_val = st.session_state.brand
        use_case_val = st.session_state.primary_use

        summary = make_filter_summary(use_case_val, budget_int, brand_val, ram_int, storage_int)

        st.markdown(
            clean_html(
                f"""
                <div style="margin: 1.5rem 0 2rem 0;">
                    <div class="page-heading">Filtering and Ranking Laptops</div>
                    <div class="summary-bar">{summary}</div>
                    <div style="font-size: 0.95rem; color: #475569; font-weight: 500;">
                        Applying budget constraints and computing nearest-neighbor rankings...
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        brands_tuple = () if brand_val == "Any brand" else (brand_val,)
        eligible = filter_catalog(
            catalog_df,
            budget=budget_int,
            brands=brands_tuple,
            min_ram_gb=ram_int,
            min_storage_gb=storage_int,
        )
        results = recommend(eligible, use_case=use_case_val, top=5)

        st.session_state.eligible_count = len(eligible)
        st.session_state.results = results
        st.session_state.filter_summary = summary
        st.session_state.search_executed = True

        st.session_state.screen = "recommendations"
        st.rerun()

    # =========================================================================
    # SCREEN 3: RECOMMENDATIONS
    # =========================================================================
    elif st.session_state.screen == "recommendations":
        render_navbar()

        results = st.session_state.get("results", pd.DataFrame())
        summary = st.session_state.get(
            "filter_summary",
            make_filter_summary(
                st.session_state.primary_use,
                parse_budget_inr(st.session_state.budget),
                st.session_state.brand,
                parse_ram_gb(st.session_state.min_ram),
                parse_storage_gb(st.session_state.min_storage),
            ),
        )

        header_col, edit_col = st.columns([0.8, 0.2])
        with header_col:
            st.markdown(
                clean_html(
                    f"""
                    <div class="page-heading">Recommendations</div>
                    <div class="summary-bar">{summary}</div>
                    """
                ),
                unsafe_allow_html=True,
            )
        with edit_col:
            st.write("")
            if st.button("Edit filters", key="btn_edit_filters", use_container_width=True):
                st.session_state.screen = "preferences"
                st.rerun()

        # Handle Empty Result State
        if results.empty:
            st.markdown(
                clean_html(
                    """
                    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 2.5rem; margin-bottom: 2rem;">
                        <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem;">
                            No laptops match the selected filters
                        </div>
                        <div style="font-size: 0.95rem; color: #475569; margin-bottom: 1.5rem; line-height: 1.5;">
                            None of the 744 catalog records met all active constraints simultaneously.
                        </div>
                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 1.25rem; margin-bottom: 1.5rem;">
                            <div style="font-weight: 600; color: #0f172a; margin-bottom: 0.5rem;">Suggestions to broaden your search:</div>
                            <ul style="color: #475569; font-size: 0.9rem; margin-bottom: 0; padding-left: 1.25rem; line-height: 1.6;">
                                <li>Increase the maximum budget cap.</li>
                                <li>Set Brand to "Any brand".</li>
                                <li>Lower or clear the minimum RAM and storage requirements.</li>
                            </ul>
                        </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
            col_b1, col_b2, col_b3 = st.columns([0.35, 0.3, 0.35])
            with col_b2:
                if st.button("Tweak filters", type="primary", key="btn_tweak_empty", use_container_width=True):
                    st.session_state.screen = "preferences"
                    st.rerun()

        else:
            # First match: Best Match
            price_model = get_trained_price_model()
            best_match = results.iloc[0]
            best_specs = format_specs_line(best_match)
            best_reason = generate_match_reason(best_match, st.session_state.primary_use)
            best_price = format_inr(best_match.get("price_inr"))
            best_name = str(best_match.get("model_name") or f"{best_match.get('brand')} Laptop")
            best_url = get_listing_url(best_match.get("shop_links"), best_match.get("best_store"))
            best_store = str(best_match.get("best_store") or "Listing").title()
            best_img_html = render_product_image_html(
                best_match.get("image_url"),
                best_match.get("id"),
                best_name,
                "best-card-img",
                is_hero=True,
            )

            best_fair = estimate_fair_price(price_model, best_match)
            best_fair_html = ""
            if best_fair:
                actual_price = best_match.get("price_inr")
                diff = actual_price - best_fair
                if abs(diff) / best_fair <= 0.05:
                    deal_text = "Priced near fair market value"
                elif diff < 0:
                    deal_text = f"₹{abs(diff):,.0f} below model estimate (Good Value)"
                else:
                    deal_text = f"Model estimate: {format_inr(best_fair)}"
                best_fair_html = f'<div class="fair-price-tag">AI/ML Model Fair Value: {format_inr(best_fair)} &middot; <span class="deal-note">{deal_text}</span></div>'

            link_html = f'<a href="{best_url}" target="_blank" class="action-link">View on {best_store}</a>' if best_url else ""

            st.markdown(
                clean_html(
                    f"""
                    <div class="best-card">
                        <div class="best-card-content">
                            <div class="best-card-info">
                                <div class="badge-label">Best Match</div>
                                <div class="laptop-title">{best_name}</div>
                                <div class="price-display">{best_price}</div>
                                {best_fair_html}
                                <div class="specs-row">{best_specs}</div>
                                <div class="reason-box"><strong>Why this fits:</strong> {best_reason}</div>
                                {link_html}
                            </div>
                            <div class="best-card-media">
                                {best_img_html}
                            </div>
                        </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

            # Alternatives (up to 4)
            alternatives = results.iloc[1:5]
            if not alternatives.empty:
                st.markdown(
                    clean_html(
                        """
                        <div style="font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 2rem; margin-bottom: 1rem;">
                            Alternative Options
                        </div>
                        """
                    ),
                    unsafe_allow_html=True,
                )

                alt_list = [alternatives.iloc[i] for i in range(len(alternatives))]
                for i in range(0, len(alt_list), 2):
                    row_cols = st.columns(2, gap="large")
                    for j in range(2):
                        idx = i + j
                        if idx < len(alt_list):
                            item = alt_list[idx]
                            i_name = str(item.get("model_name") or f"{item.get('brand')} Laptop")
                            i_price = format_inr(item.get("price_inr"))
                            i_specs = format_specs_line(item)
                            i_reason = generate_match_reason(item, st.session_state.primary_use)
                            i_url = get_listing_url(item.get("shop_links"), item.get("best_store"))
                            i_store = str(item.get("best_store") or "Listing").title()
                            i_img_html = render_product_image_html(
                                item.get("image_url"),
                                item.get("id"),
                                i_name,
                                "alt-img",
                                is_hero=False,
                            )
                            rank_num = idx + 2

                            i_link_html = f'<a href="{i_url}" target="_blank" class="alt-link">View on {i_store}</a>' if i_url else ""
                            i_fair = estimate_fair_price(price_model, item)
                            i_fair_html = f'<div class="alt-fair-price">ML Fair Value: {format_inr(i_fair)}</div>' if i_fair else ""

                            with row_cols[j]:
                                st.markdown(
                                    clean_html(
                                        f"""
                                        <div class="alt-item">
                                            <div>
                                                <div class="alt-media">
                                                    {i_img_html}
                                                </div>
                                                <div class="alt-rank">Option {rank_num}</div>
                                                <div class="alt-title">{i_name}</div>
                                                <div class="alt-price">{i_price}</div>
                                                {i_fair_html}
                                                <div class="alt-specs">{i_specs}</div>
                                                <div class="alt-reason">{i_reason}</div>
                                            </div>
                                            {i_link_html}
                                        </div>
                                        """
                                    ),
                                    unsafe_allow_html=True,
                                )
                    st.write("")

            st.markdown(
                clean_html(
                    """
                    <div style="font-size: 0.8rem; color: #64748b; font-style: italic; margin-top: 2rem;">
                        Observed snapshot prices. Retail availability and current market pricing may vary.
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

        render_footer()


if __name__ == "__main__":
    main()
