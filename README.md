# Laptop Finder - Engineering Project

A catalog filtering and ranking system for the Indian laptop market. The application enables users to filter laptops by budget cap in INR and workflow requirements (Gaming, Student/Office, Programming, Video Editing, AI/ML, Portability, or Value for Money) using metric-space nearest-neighbor ranking.

---

## Quickstart: Local Setup and Launch

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Export and Refresh Datasets from SQLite Snapshot
```bash
python scraper.py export
python scripts/cache_all_images.py
```
Exports `data/exports/laptops.csv` (744 catalog entries), `data/exports/laptops_ml_ready.csv` (744 feature rows), and pre-caches optimized WebP product images in `data/cache/images/` for instant offline rendering.

### 3. Launch the Streamlit Web Application
```bash
streamlit run streamlit_app.py
```
Open `http://localhost:8501` in your browser.

---

## Application Interface

The interface provides direct access to search parameters and delivers structured catalog results:

1. **Search and Filter Interface (Direct Entry)**:
   - Form inputs: Maximum budget in INR and primary workflow.
   - Optional hardware constraints: Brand, Minimum RAM, and Minimum storage.
   - Primary submission button: "Find laptops".

2. **Matching Indicator**:
   - Active during calculation.
   - Retains active filter summary while ranking runs.

3. **Recommendations Screen**:
   - **Best Match**: Displays top-ranked laptop with observed catalog price, full hardware specs line, match rationale, and retailer link.
   - **Alternative Options**: Displays up to 4 alternative options in a two-column grid.
   - **Edit Filters**: Preserves previous selections and returns to the search form.
   - **Zero-Matches State**: When constraints eliminate all models, actionable guidance explains how to broaden parameters (e.g., raise budget, set Brand to "Any brand", remove RAM/storage minimums).

---

## Verification Presets

### Preset 1: Student / Office (Budget Cap: INR 60,000)
- **Budget**: INR 60,000
- **Primary Use**: Student / Office
- **Brand**: Any brand
- **RAM**: Any RAM
- **Storage**: Any storage
- **Behavior**: Filters catalog strictly to models priced at or below INR 60,000. Prioritizes efficient processors, solid-state storage, and balanced productivity memory.

### Preset 2: Gaming (Budget Cap: INR 90,000)
- **Budget**: INR 90,000
- **Primary Use**: Gaming
- **Brand**: Any brand
- **RAM**: 16 GB
- **Storage**: 512 GB
- **Behavior**: Enforces the INR 90,000 cap and hardware minimums. Ranks models with dedicated GPUs (e.g. RTX 4060, RTX 4050, RTX 3050) and high-performance CPUs.

### Preset 3: Zero-Match Constraint Check
- **Budget**: INR 30,000
- **Primary Use**: Gaming
- **RAM**: 32 GB
- **Behavior**: Accurately detects that no catalog records meet all criteria simultaneously, clears previous results, renders guidance, and preserves filter selections when editing.

---

## Catalog Snapshot and Data Integrity

- **Primary Source**: E-commerce catalog snapshot stored in SQLite (`data/scraper.db`).
- **Record Count**: 744 catalog rows and 744 feature rows in `laptops_ml_ready.csv`.
- **Integrity**: 0 duplicate IDs; 100% one-to-one join on `laptops.csv.id = laptops_ml_ready.csv.laptop_id`.
- **Price Handling**:
  - 688 products contain positive catalog snapshot prices (`price_inr > 0`).
  - 56 products have unlisted catalog prices (`price_inr is NaN`). These items are excluded from budget-constrained searches in `filter_catalog` to avoid false price promises.
- **Snapshot Pricing**: Prices reflect observed snapshot values. Live retail availability may vary.

---

## Recommendation and Ranking Architecture

### 1. Constraint Filtering (`filter_catalog`)
User constraints are evaluated prior to ranking:
- Budget: `catalog.price_inr <= budget` (hard cap; excludes unpriced items).
- Brand: Matches selected brands (case-insensitive OR).
- RAM and Storage: Evaluated against observed hardware specifications. Missing values fail only when a specific minimum is active.

### 2. Nearest-Neighbor Metric Space (`recommend`)
Laptops are mapped into a Euclidean metric space:
- Dimension 1: Normalized Use-Case Score ($u / 100 \times \sqrt{0.8}$)
- Dimension 2: Normalized Value-for-Money Score ($v / 100 \times \sqrt{0.2}$)
- Query Point: Euclidean nearest neighbor to $(1.0 \times \sqrt{0.8}, 1.0 \times \sqrt{0.2})$.
- Value Use-Case: For "Value for Money", queries distance to 1.0 along the value score dimension alone.
- Deterministic Tie-Breaking:
  1. Metric distance ascending
  2. Specification completeness (`score_confidence`) descending
  3. Catalog price ascending
  4. Numeric ID ascending

---

## Supervised Machine Learning Model Training (Price Prediction)

In addition to nearest-neighbor recommendation ranking, the project includes a supervised machine learning regression pipeline that predicts a laptop's fair market price from its hardware specifications.

To train and evaluate the models:

```bash
python train_model.py
```

### Models Evaluated (80/20 Split on 688 Real Observed Catalog Laptops)

| Model | Test MAE (INR) | Test RMSE (INR) | Test $R^2$ Score | 5-Fold CV Mean $R^2$ |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline (Median)** | ₹52,985 | ₹97,214 | -0.078 | N/A |
| **Ridge Regression** | ₹22,852 | ₹37,708 | 0.811 | 0.754 |
| **HistGradientBoosting** | ₹21,642 | ₹36,812 | 0.820 | 0.768 |
| **Random Forest (Best)** | **₹20,887** | **₹34,609** | **0.841** | **0.781** |

The trained Random Forest pipeline is serialized and saved to:
`models/laptop_price_model.joblib`

An interactive Jupyter Notebook detailing EDA, feature engineering, model training, residual analysis, and feature importances is available at:
[`data/exports/Laptop_Price_Evaluation.ipynb`](data/exports/Laptop_Price_Evaluation.ipynb)

---

## Automated Test Suite

Run the full automated test suite covering pipeline normalization, recommender edge cases, model inference, and Streamlit `AppTest` workflows:

```bash
python -m pytest tests -v
```

Test suite coverage (40 tests):
- 2 tests in `tests/test_model.py`: Model artifact validation, loading, and realistic inference testing.
- 14 tests in `tests/test_pipeline.py`: Hardware normalization, parsing rules, and score calculations.
- 19 tests in `tests/test_recommender.py`: CSV header cleaning, schema validation, budget boundary conditions, tie-breaking, and formatters.
- 5 tests in `tests/test_streamlit_app.py`: Direct search view rendering, budget adherence, edit-and-resubmit flow, and empty-state handling.

---

## Benchmark Evaluation Results

The Nearest-Neighbor Recommender was evaluated against a Cheapest-First baseline across 6 benchmark scenarios:

```bash
python scripts/evaluate_recommender.py
```

| Scenario | Use Case | Budget | Eligible Count | Recommender Precision@5 | Cheapest-First Precision@5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **scenario_1_gaming_70k** | Gaming | INR 70,000 | 87 | **60.0%** (3/5) | 0.0% (0/5) |
| **scenario_2_student_50k** | Student/Office | INR 50,000 | 51 | **100.0%** (5/5) | 100.0% (5/5) |
| **scenario_3_programming_80k** | Programming | INR 80,000 | 142 | **100.0%** (5/5) | 80.0% (4/5) |
| **scenario_4_video_editing_100k** | Video Editing | INR 100,000 | 246 | **100.0%** (5/5) | 0.0% (0/5) |
| **scenario_5_portability_75k** | Portability | INR 75,000 | 220 | **100.0%** (5/5) | 60.0% (3/5) |
| **scenario_6_zero_match** | Zero-Match | INR 25,000 | 0 | N/A (0/0) | N/A (0/0) |

Detailed methodology and candidate labels are documented in [`evaluation/RESULTS.md`](evaluation/RESULTS.md).
