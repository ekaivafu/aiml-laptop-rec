"""Generate high-resolution academic figures for the project report."""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from recommender import load_catalog
CATALOG_PATH = BASE_DIR / "data" / "exports" / "laptops.csv"
FEATURES_PATH = BASE_DIR / "data" / "exports" / "laptops_ml_ready.csv"
MODEL_PATH = BASE_DIR / "models" / "laptop_price_model.joblib"
OUT_DIR = BASE_DIR / "docs" / "report_figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Set clean aesthetic styling suitable for print / PDF
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "bold",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 14,
    "figure.titleweight": "bold",
    "figure.dpi": 300,
})

def main():
    merged = load_catalog(CATALOG_PATH, FEATURES_PATH)
    real = merged[merged["price_inr"].notna() & (merged["price_inr"] > 0)].copy()

    # 1. Price Distribution (Raw vs Log Transformed)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    sns.histplot(real["price_inr"] / 1000, kde=True, ax=ax1, color="#1e3a8a", bins=30)
    ax1.set_title("Figure 3.1: Raw Price Distribution (in Thousand INR)")
    ax1.set_xlabel("Price (Thousands INR)")
    ax1.set_ylabel("Frequency (Count)")
    ax1.axvline((real["price_inr"] / 1000).median(), color="#dc2626", linestyle="--", label=f"Median: ₹{real['price_inr'].median():,.0f}")
    ax1.legend()

    sns.histplot(np.log1p(real["price_inr"]), kde=True, ax=ax2, color="#0d9488", bins=30)
    ax2.set_title("Figure 3.2: Log-Transformed Price ln(1 + Price)")
    ax2.set_xlabel("ln(1 + Price)")
    ax2.set_ylabel("Frequency (Count)")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "figure_1_eda_price_distribution.png", dpi=300)
    plt.close()
    print("Saved figure_1_eda_price_distribution.png")

    # 2. Correlation Matrix Heatmap
    corr_cols = [
        "price_inr", "ram_gb", "storage_gb", "cpu_cores", "cpu_max_clock_ghz",
        "gpu_vram_gb", "screen_size_in", "weight_kg", "battery_wh"
    ]
    corr_data = real[corr_cols].dropna().corr()
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr_data, annot=True, fmt=".2f", cmap="Blues", cbar=True, ax=ax, linewidths=0.5)
    ax.set_title("Figure 3.3: Pearson Correlation Heatmap of Hardware Attributes")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "figure_2_feature_correlation.png", dpi=300)
    plt.close()
    print("Saved figure_2_feature_correlation.png")

    # 3. Model Comparison Metrics (MAE, RMSE, R2)
    models = ["Baseline (Median)", "Ridge Regression", "HistGradientBoosting", "Random Forest"]
    mae_vals = [52985, 22852, 21642, 20887]
    r2_vals = [-0.078, 0.811, 0.820, 0.841]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    bars1 = ax1.bar(models, [m / 1000 for m in mae_vals], color=["#94a3b8", "#38bdf8", "#6366f1", "#1e3a8a"], width=0.55)
    ax1.set_title("Figure 6.1: Mean Absolute Error (MAE in Thousands INR)")
    ax1.set_ylabel("MAE (₹ Thousands)")
    ax1.set_xticklabels(models, rotation=20, ha="right")
    for bar in bars1:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2.0, yval + 1, f"₹{yval:.1f}k", ha="center", va="bottom", fontsize=9, fontweight="bold")

    bars2 = ax2.bar(models, r2_vals, color=["#94a3b8", "#38bdf8", "#6366f1", "#10b981"], width=0.55)
    ax2.set_title("Figure 6.2: Model Goodness-of-Fit (R² Score)")
    ax2.set_ylabel("R² Score")
    ax2.set_ylim(-0.2, 1.0)
    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_xticklabels(models, rotation=20, ha="right")
    for bar in bars2:
        yval = bar.get_height()
        va = "bottom" if yval >= 0 else "top"
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + (0.03 if yval >= 0 else -0.05), f"{yval:.3f}", ha="center", va=va, fontsize=9, fontweight="bold")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "figure_3_model_comparison_metrics.png", dpi=300)
    plt.close()
    print("Saved figure_3_model_comparison_metrics.png")

    # 4. Actual vs Predicted Price Scatter Plot
    if MODEL_PATH.exists():
        artifact = joblib.load(MODEL_PATH)
        pipeline = artifact["model"]
        num_cols = artifact["num_cols"]
        cat_cols = artifact["cat_cols"]
        X = real[num_cols + cat_cols].copy()
        y = real["price_inr"].copy()

        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        y_pred = np.expm1(pipeline.predict(X_test))

        fig, ax = plt.subplots(figsize=(7.5, 6))
        ax.scatter(y_test / 1000, y_pred / 1000, alpha=0.7, color="#1e3a8a", edgecolors="w", s=50, label="Test Laptops (N=138)")
        max_val = max(y_test.max(), y_pred.max()) / 1000
        ax.plot([0, max_val], [0, max_val], color="#dc2626", linestyle="--", linewidth=1.5, label="Ideal 1:1 Parity Line")
        ax.set_title("Figure 6.3: Random Forest Price Predictions vs. Actual Catalog Prices")
        ax.set_xlabel("Actual Catalog Price (Thousands INR)")
        ax.set_ylabel("Predicted Price (Thousands INR)")
        ax.legend(loc="upper left")
        plt.tight_layout()
        fig.savefig(OUT_DIR / "figure_4_actual_vs_predicted.png", dpi=300)
        plt.close()
        print("Saved figure_4_actual_vs_predicted.png")

        # 5. Feature Importances
        rf_step = pipeline.named_steps["rf"]
        preprocessor = pipeline.named_steps["pre"]
        cat_feature_names = list(preprocessor.named_transformers_["cat"].get_feature_names_out(cat_cols))
        all_feature_names = num_cols + cat_feature_names
        importances = rf_step.feature_importances_
        imp_df = pd.DataFrame({"Feature": all_feature_names, "Importance": importances}).sort_values(by="Importance", ascending=True).tail(10)

        fig, ax = plt.subplots(figsize=(8.5, 5))
        ax.barh(imp_df["Feature"], imp_df["Importance"], color="#2563eb", height=0.6)
        ax.set_title("Figure 6.4: Top 10 Most Influential Features (Random Forest Gini Importance)")
        ax.set_xlabel("Relative Importance")
        plt.tight_layout()
        fig.savefig(OUT_DIR / "figure_5_feature_importance.png", dpi=300)
        plt.close()
        print("Saved figure_5_feature_importance.png")

    # 6. Recommender Precision@5 vs Baseline Grouped Bar Chart
    scenarios = [
        "Gaming\n₹70k", "Student\n₹50k", "Programming\n₹80k",
        "Video Edit\n₹100k", "Portability\n₹75k"
    ]
    rec_prec = [0.60, 1.00, 1.00, 1.00, 1.00]
    cheap_prec = [0.00, 1.00, 0.80, 0.00, 0.60]

    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    rects1 = ax.bar(x - width/2, [p * 100 for p in rec_prec], width, label="Nearest-Neighbor Recommender", color="#1e3a8a")
    rects2 = ax.bar(x + width/2, [p * 100 for p in cheap_prec], width, label="Cheapest-First Baseline", color="#94a3b8")

    ax.set_title("Figure 6.5: Hardware Suitability (Precision@5 %) Across 5 Search Scenarios")
    ax.set_ylabel("Precision@5 (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    ax.set_ylim(0, 115)
    ax.legend(loc="lower right")

    for rect in rects1:
        height = rect.get_height()
        ax.annotate(f"{height:.0f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold", color="#1e3a8a")

    for rect in rects2:
        height = rect.get_height()
        ax.annotate(f"{height:.0f}%", xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontweight="bold", color="#475569")

    plt.tight_layout()
    fig.savefig(OUT_DIR / "figure_6_recommender_precision_benchmark.png", dpi=300)
    plt.close()
    print("Saved figure_6_recommender_precision_benchmark.png")

if __name__ == "__main__":
    main()
