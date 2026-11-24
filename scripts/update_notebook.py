import json

def update():
    nb_path = "data/exports/Laptop_Price_Evaluation.ipynb"
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Check if cell 13 already added
    sources = ["".join(c["source"]) for c in nb["cells"]]
    if any("CELL 13" in s for s in sources):
        print("CELL 13 already present.")
        return

    cell13 = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ------------------------------------------------------------\n",
            "# CELL 13 - Supervised Model Training & Evaluation\n",
            "# ------------------------------------------------------------\n",
            "from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor\n",
            "from sklearn.linear_model import Ridge\n",
            "from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error\n",
            "import joblib\n",
            "\n",
            "# 1. Baseline Median\n",
            "med_val = y_train.median()\n",
            "y_pred_base = np.full_like(y_test, med_val)\n",
            "base_mae = mean_absolute_error(y_test, y_pred_base)\n",
            "base_r2 = r2_score(y_test, y_pred_base)\n",
            "\n",
            "# 2. Ridge Regression\n",
            "ridge = Ridge(alpha=1.0)\n",
            "ridge.fit(X_train_scaled, np.log1p(y_train))\n",
            "y_pred_ridge = np.expm1(ridge.predict(X_test_scaled))\n",
            "ridge_mae = mean_absolute_error(y_test, y_pred_ridge)\n",
            "ridge_r2 = r2_score(y_test, y_pred_ridge)\n",
            "\n",
            "# 3. HistGradientBoosting\n",
            "hgb = HistGradientBoostingRegressor(max_iter=150, random_state=42)\n",
            "hgb.fit(X_train_scaled, np.log1p(y_train))\n",
            "y_pred_hgb = np.expm1(hgb.predict(X_test_scaled))\n",
            "hgb_mae = mean_absolute_error(y_test, y_pred_hgb)\n",
            "hgb_r2 = r2_score(y_test, y_pred_hgb)\n",
            "\n",
            "# 4. Random Forest Regressor\n",
            "rf = RandomForestRegressor(n_estimators=200, max_depth=16, random_state=42, n_jobs=-1)\n",
            "rf.fit(X_train_scaled, np.log1p(y_train))\n",
            "y_pred_rf = np.expm1(rf.predict(X_test_scaled))\n",
            "rf_mae = mean_absolute_error(y_test, y_pred_rf)\n",
            "rf_rmse = root_mean_squared_error(y_test, y_pred_rf)\n",
            "rf_r2 = r2_score(y_test, y_pred_rf)\n",
            "\n",
            "print('=== SUPERVISED REGRESSION BENCHMARK ===')\n",
            "print(f'Baseline Median:      MAE = INR {base_mae:,.0f} | R2 = {base_r2:.3f}')\n",
            "print(f'Ridge Regression:     MAE = INR {ridge_mae:,.0f} | R2 = {ridge_r2:.3f}')\n",
            "print(f'HistGradientBoosting: MAE = INR {hgb_mae:,.0f} | R2 = {hgb_r2:.3f}')\n",
            "print(f'Random Forest:        MAE = INR {rf_mae:,.0f} | RMSE = INR {rf_rmse:,.0f} | R2 = {rf_r2:.3f}')\n"
        ]
    }

    cell14 = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ------------------------------------------------------------\n",
            "# CELL 14 - Actual vs Predicted & Feature Importances\n",
            "# ------------------------------------------------------------\n",
            "plt.figure(figsize=(12, 5))\n",
            "plt.subplot(1, 2, 1)\n",
            "plt.scatter(y_test, y_pred_rf, alpha=0.6, color='#0f172a')\n",
            "max_val = max(y_test.max(), y_pred_rf.max())\n",
            "plt.plot([0, max_val], [0, max_val], 'r--', label='Perfect Fit')\n",
            "plt.xlabel('Actual Catalog Price (₹)')\n",
            "plt.ylabel('Predicted Price (₹)')\n",
            "plt.title(f'Random Forest: Actual vs Predicted (R² = {rf_r2:.3f})')\n",
            "plt.legend()\n",
            "\n",
            "plt.subplot(1, 2, 2)\n",
            "importances = pd.Series(rf.feature_importances_, index=feature_cols).sort_values(ascending=False).head(10)\n",
            "importances.plot(kind='barh', color='#334155')\n",
            "plt.title('Top 10 Feature Importances')\n",
            "plt.xlabel('Gini Importance')\n",
            "plt.gca().invert_yaxis()\n",
            "plt.tight_layout()\n",
            "plt.show()\n"
        ]
    }

    cell15 = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# ------------------------------------------------------------\n",
            "# CELL 15 - Save Trained Model Artifact\n",
            "# ------------------------------------------------------------\n",
            "import os\n",
            "os.makedirs('../../models', exist_ok=True)\n",
            "joblib.dump(rf, '../../models/laptop_price_model_standalone.joblib')\n",
            "print('Trained model successfully saved to models/laptop_price_model_standalone.joblib')\n"
        ]
    }

    nb["cells"].extend([cell13, cell14, cell15])

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)

    print("Notebook successfully updated with Cells 13, 14, and 15!")

if __name__ == "__main__":
    update()
