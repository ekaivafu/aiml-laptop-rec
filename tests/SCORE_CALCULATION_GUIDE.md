# Laptop Recommendation System: Scoring Methodology & Feature Mapping Guide

## 1. Executive Summary & Conceptual Architecture

This project is an **AI/ML laptop recommendation system tailored for the Indian market**, collecting and structuring laptop hardware specifications exclusively from **Smartprix**.

To ensure academic and technical defensibility for a college AI/ML subject, the system is conceptually divided into **three stages plus downstream machine learning**:

```
 ┌─────────────────────────┐
 │ Stage 1: Raw Collection │ ── Smartprix HTML / JSON-LD / Queue (scraper.db)
 └────────────┬────────────┘
              │
              ▼
 ┌─────────────────────────┐
 │ Stage 2: Normalization  │ ── Factual Hardware Parsing, Units Cleaning,
 └────────────┬────────────┘    Project-Defined Normalized Tiers (CPU/GPU)s
              │
              ▼
 ┌─────────────────────────┐
 │ Stage 3: Heuristic      │ ── 7 Domain Benchmark Scores (0–100) +
 │          Feature Matrix │    Score Confidence Reliability Metric (0.0–1.0)
 └────────────┬────────────┘
              │
              ▼
 ┌─────────────────────────┐
 │ Stage 4: Downstream ML  │ ── Recommendation Models (KNN, Cosine Similarity,
 │          Models         │    K-Means Persona Clustering, Learning-to-Rank)
 └─────────────────────────┘
```

> [!IMPORTANT]
> **CRITICAL DISTINCTION FOR VIVA / PROJECT DEFENSE:**
> The **7 use-case scores (0–100) are domain-knowledge engineered heuristic features**, **NOT the machine learning model itself**.
> 
> In applied Machine Learning, domain expertise is used to transform raw categorical and text data into dense, interpretable numeric representations. The downstream ML model (such as Content-Based Filtering, KNN, K-Means Clustering, or LightGBM Ranking) uses **both** the raw normalized hardware features (`price_inr`, `ram_gb`, `cpu_cores`, `weight_kg`) and these **7 engineered domain scores** to deliver personalized recommendations.

---

## 2. Project-Defined Normalized Performance Tiers

Smartprix provides factual hardware names (e.g., `Intel Core i7 13620H`, `NVIDIA GeForce RTX 4060`), but does not publish synthetic benchmark figures (like Cinebench R23 or 3DMark TimeSpy). 

To avoid inventing fake benchmark data while still allowing machine learning algorithms to process hardware hierarchy numerically, we define **Project-Defined Normalized Performance Tiers**:

### A. CPU Tier (`cpu_tier`: 1 to 5)
An ordinal grouping derived strictly from processor series and architecture stated on Smartprix:
- **Tier 1 (Entry)**: Intel Celeron, Pentium, AMD Athlon (Basic web tasks).
- **Tier 2 (Budget)**: Intel Core i3, AMD Ryzen 3 (Everyday productivity).
- **Tier 3 (Mainstream)**: Intel Core i5, AMD Ryzen 5, Core Ultra 5, Apple M1/M2 (Multitasking, coding, casual gaming).
- **Tier 4 (High Performance)**: Intel Core i7, AMD Ryzen 7, Core Ultra 7, Apple M3/M4 (Heavy compilation, 1440p gaming, 4K rendering).
- **Tier 5 (Enthusiast / Flagship)**: Intel Core i9, AMD Ryzen 9, Intel HX-series, Apple M Max/Pro (Workstation 3D simulation, heavy deep learning).

*Note: We do not claim an older i7 is universally faster than a newer i5 across all synthetic benchmarks; rather, this tier reflects the processor's market tier and multi-core silicon positioning.*

### B. GPU Tier (`gpu_tier`: 0 to 5)
An ordinal grouping derived strictly from GPU family and discrete memory classification:
- **Tier 0 (Basic Integrated)**: Intel UHD, AMD basic iGPU (0 GB dedicated VRAM).
- **Tier 1 (Performance Integrated)**: Intel Iris Xe, AMD Radeon 680M/780M, Apple 8/10-Core iGPU (0 GB dedicated VRAM).
- **Tier 2 (Entry Dedicated)**: NVIDIA GTX 1650, RTX 2050, RTX 3050 (4 GB GDDR6).
- **Tier 3 (Mid-Range Dedicated)**: NVIDIA RTX 3060, RTX 4050 (6 GB GDDR6).
- **Tier 4 (High-End Dedicated)**: NVIDIA RTX 4060, RTX 4070, RTX 5050/5060 (8 GB GDDR6).
- **Tier 5 (Flagship Dedicated)**: NVIDIA RTX 4080, RTX 4090 (12–16 GB GDDR6), Apple M Max.

---

## 3. Table 1: Final Scoring Table

This table defines all 7 domain-engineered scores, their mathematical purpose, input features, exact weights, normalization curves, and real-world interpretations:

| Score | Purpose | Input Features | Weights | Normalization Method | Interpretation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`score_gaming`** | Evaluates real-time 3D rendering and gaming frame rates | `gpu_tier`, `gpu_vram_gb`, `refresh_rate_hz`, `cpu_tier`, `cpu_max_ghz`, `ram_gb` | **GPU: 50%**<br>**CPU: 20%**<br>**RAM: 15%**<br>**Display Hz: 15%** | **GPU**: Tier (0–5) + VRAM (up to 8GB)<br>**Hz**: Smooth saturation (60Hz=45, 120Hz=85, 144Hz=95, 165Hz+=100)<br>**CPU**: Tier + Clock ($\le 5.0$ GHz)<br>**RAM**: Diminishing return (8GB=50, 16GB=85, 24GB=95, 32GB=100) | **$\ge 80$**: AAA gaming at 1080p/1440p High/Ultra<br>**60–79**: Budget 1080p gaming (RTX 2050/3050)<br>**$< 40$**: Non-gaming / basic integrated GPU |
| **`score_aiml`** | Evaluates local AI development, model training, and LLM inference | `gpu_brand`, `is_dedicated_gpu`, `gpu_vram_gb`, `ram_gb`, `cpu_cores`, `cpu_tier` | **GPU/CUDA: 35%**<br>**VRAM: 25%**<br>**System RAM: 20%**<br>**CPU Multi-Core: 20%** | **CUDA**: NVIDIA=100, Apple MPS=45, Intel/AMD=15<br>**VRAM**: Scaling up to 16GB VRAM<br>**RAM**: Scaling up to 32GB system RAM<br>**CPU**: Multi-core preprocessing ($\le 16$ cores) | **$\ge 75$**: Local PyTorch/TensorFlow training with CUDA & 8GB+ VRAM<br>**40–74**: Apple Silicon / entry discrete AI experimentation<br>**$< 30$**: CPU-only basic scikit-learn |
| **`score_video_editing`** | Evaluates timeline playback, video export, and multi-track rendering | `gpu_tier`, `gpu_vram_gb`, `cpu_threads`, `cpu_tier`, `resolution_width`, `is_oled`, `brightness_nits`, `ram_gb` | **GPU: 30%**<br>**CPU: 30%**<br>**Display: 20%**<br>**RAM: 20%** | **GPU**: NVENC/hardware acceleration<br>**CPU**: Multi-threaded export ($\le 16$ threads)<br>**Display**: Resolution width ($\le 2560$) + OLED bonus + Nits ($\le 400$)<br>**RAM**: 16GB baseline (80 pts), 32GB (100 pts) | **$\ge 80$**: Smooth 4K ProRes/H.265 timeline with color grading<br>**60–79**: 1080p and light 4K YouTube editing<br>**$< 45$**: Basic video clip trimming |
| **`score_programming`** | Evaluates code compilation speed, Docker containers, and IDE multitasking | `cpu_cores`, `cpu_max_ghz`, `ram_gb`, `storage_gb`, `is_ssd`, `resolution_height`, `is_anti_glare` | **CPU: 35%**<br>**RAM: 35%**<br>**Storage: 15%**<br>**Ergonomics: 15%** | **CPU**: Parallel compilation ($\le 12$ cores) + single-core burst ($\le 4.8$ GHz)<br>**RAM**: Heavy multitasking (16GB=85, 32GB=100)<br>**Storage**: SSD speed + capacity ($\le 1024$ GB)<br>**Display**: Vertical resolution ($\ge 1200\text{p}$) + Anti-glare bonus | **$\ge 80$**: Full-stack dev with multiple containers, VMs, IDEs<br>**60–79**: Standard web/app development<br>**$< 50$**: Light scripting / basic computer science coursework |
| **`score_portability`** | Evaluates everyday carrying comfort and battery endurance | `weight_kg`, `thickness_mm`, `battery_wh` | **Weight: 50%**<br>**Thickness: 25%**<br>**Battery: 25%**<br>*(Dynamic redistribution if battery missing)* | **Weight**: Linear decline from 1.1kg (100) to 2.8kg (20)<br>**Thickness**: Linear decline from 11mm (100) to 26mm (30)<br>**Battery**: Scaling up to 80Wh (100 pts) | **$\ge 80$**: Ultralight traveler ($\le 1.4\text{ kg}$, all-day battery)<br>**60–79**: Standard office commuter (1.6–1.8 kg)<br>**$< 50$**: Heavy desk-bound gaming laptop ($\ge 2.3\text{ kg}$) |
| **`score_student_office`** | Evaluates student coursework, MS Office, Zoom calls, and budget suitability | `score_portability`, `price_inr`, `battery_wh`, `screen_size_in`, `brightness_nits` | **Portability: 35%**<br>**Affordability: 35%**<br>**Battery: 15%**<br>**Display: 15%** | **Portability**: Carried from score_portability<br>**Affordability**: Smooth diminishing curve favoring ₹25k–₹70k in India<br>**Battery**: Endurance ($\le 70\text{ Wh}$)<br>**Display**: Comfortable viewing | **$\ge 75$**: Ideal student laptop (light, long battery, affordable)<br>**60–74**: Capable everyday office laptop<br>**$< 50$**: Unsuitable (too expensive, too heavy, or short battery) |
| **`score_value_for_money`** | Evaluates hardware capability density per Rupee spent in India | `score_gaming`, `score_programming`, `score_video_editing`, `price_inr` | **Utility: 100%** normalized against **Price Elasticity** | **Hardware Utility**: Composite average of Core Workloads<br>**Price Ratio**: Hardware capability divided by power-law price elasticity $(\text{price} / 50000)^{0.65}$ | **$\ge 80$**: Outstanding performance per Rupee (budget gaming / value ultrabook)<br>**60–79**: Fair market price for hardware offered<br>**$< 50$**: Premium luxury markup (low hardware density per Rupee) |

---

## 4. Table 2: Feature Mapping Table

This table maps each physical hardware attribute from Smartprix to the scores it influences and documents the technical rationale:

| Hardware Attribute | Raw Format on Smartprix | Normalized Field in DB | Scores Directly Influenced | Technical Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Price (INR)** | `"₹80,999"` | `price_inr` (Float) | `score_student_office`<br>`score_value_for_money` | Direct constraint on budget affordability; denominator in price-to-performance efficiency. |
| **CPU Family & Model** | `"13th Gen Intel Core i7 13620H"` | `cpu_tier` (Int: 1–5)<br>`cpu_model` (String) | `score_gaming`<br>`score_aiml`<br>`score_video_editing`<br>`score_programming` | Determines microarchitecture IPC and silicon tier for compilation, rendering, and game logic. |
| **CPU Cores & Threads** | `"10 Cores (6P + 4E), 16 Threads"` | `cpu_cores` (Int)<br>`cpu_threads` (Int) | `score_programming`<br>`score_video_editing`<br>`score_aiml` | Parallel processing capacity for multi-threaded video encoding, Docker containers, and data batching. |
| **CPU Max Clock** | `"Turbo Speed upto 4.9 GHz"` | `cpu_max_ghz` (Float) | `score_gaming`<br>`score_programming` | High single-core burst frequency directly governs game frame rates and compilation responsiveness. |
| **GPU Model & Brand** | `"NVIDIA GeForce RTX 4060"` | `gpu_brand` (String)<br>`gpu_tier` (Int: 0–5)<br>`is_dedicated_gpu` (Bool) | `score_gaming`<br>`score_aiml`<br>`score_video_editing` | 3D rasterization for gaming, NVENC for video export, and CUDA tensor cores for AI/ML acceleration. |
| **GPU Dedicated VRAM** | `"GDDR6 8 GB"` | `gpu_vram_gb` (Float) | `score_gaming`<br>`score_aiml`<br>`score_video_editing` | Texture buffer size for gaming; limits maximum parameter size and batch size for deep learning models. |
| **RAM Capacity** | `"16 GB LPDDR5"` | `ram_gb` (Int) | `score_gaming`<br>`score_aiml`<br>`score_video_editing`<br>`score_programming` | Multi-tasking headroom; holding large datasets in memory; prevents swapping to disk under heavy loads. |
| **Display Refresh Rate** | `"144 Hz"` | `refresh_rate_hz` (Int) | `score_gaming` | Frame rate smoothness; higher refresh rates reduce latency and motion blur in fast-paced gaming. |
| **Display Resolution** | `"1920 x 1200 pixels"` | `resolution_width` (Int)<br>`resolution_height` (Int) | `score_video_editing`<br>`score_programming` | Pixel real estate for 4K video preview and vertical lines of code visible in IDEs. |
| **Display Panel & Nits** | `"300nits, 100% sRGB"` | `brightness_nits` (Int)<br>`is_oled` (Bool) | `score_video_editing`<br>`score_student_office` | Color accuracy and outdoor/office readability under bright fluorescent lighting. |
| **Display Anti-Glare** | `"Anti Glare Screen: Yes"` | `is_anti_glare` (Bool) | `score_programming` | Eye strain reduction during 8+ hour coding sessions. |
| **Weight** | `"1.62 kg"` | `weight_kg` (Float) | `score_portability`<br>`score_student_office` | Primary physical metric determining whether a laptop is comfortable to carry in a backpack. |
| **Thickness** | `"17.9 mm"` | `thickness_mm` (Float) | `score_portability` | Slimness and ergonomic profile for bag storage and mobility. |
| **Battery Capacity** | `"60 Wh, 4 Cell"` | `battery_wh` (Float) | `score_portability`<br>`score_student_office` | Watt-hour capacity directly governs off-charger endurance during classes or commute. |

---

## 5. Missing Values & Dynamic Weight Redistribution

A major flaw in naive scoring systems is treating missing fields as $0$. For example, if Smartprix does not list `battery_wh`, that does **not** mean the laptop has zero battery!

### A. Distinction Between Genuine Zero vs Missing:
- **Genuine Zero**: If `has_dedicated_gpu == False`, then `gpu_vram_gb = 0.0` is genuine (integrated graphics share system RAM).
- **Missing Value**: If `battery_wh` is NULL, it is missing information, not a 0-watt battery.

### B. Dynamic Weight Redistribution (Portability Example):
The standard Portability formula is:
$$\text{Portability} = 0.50 \times \text{Weight} + 0.25 \times \text{Thickness} + 0.25 \times \text{Battery}$$

If `battery_wh` is missing from the Smartprix table:
1. We do **not** plug in 0 for Battery.
2. The remaining weights ($0.50 + 0.25 = 0.75$) are dynamically redistributed to 100%:
   $$\text{Weight Weight} = \frac{0.50}{0.75} \approx 0.67 \quad (67\%)$$
   $$\text{Thickness Weight} = \frac{0.25}{0.75} \approx 0.33 \quad (33\%)$$
   $$\text{score\_portability} = 0.67 \times \text{Weight} + 0.33 \times \text{Thickness}$$
This ensures the laptop is neither unfairly penalized nor artificially inflated.

---

## 6. Score Confidence Indicator (`score_confidence`: 0.0 – 1.0)

To provide transparency regarding data completeness, every record in `ml_laptop_features` includes a **`score_confidence`** reliability indicator:

$$\text{score\_confidence} = \frac{\sum_{i=1}^{8} \text{Available Essential Feature}_i}{8.0}$$

The 8 monitored essential features are:
1. `price_inr`
2. `cpu_cores`
3. `ram_gb`
4. `storage_gb`
5. `screen_size_in`
6. `weight_kg`
7. `battery_wh`
8. `brightness_nits`

### Confidence Tiers:
- **High Confidence ($\ge 0.85$)**: 7 or 8 specs verified from Smartprix. Highly dependable score.
- **Medium Confidence ($0.70 – 0.84$)**: 6 specs verified (e.g. battery or brightness imputed). Good reliability.
- **Low Confidence ($< 0.70$)**: Multiple specifications missing. Scores should be treated as indicative estimates.

---

## 7. Calibrated Value-for-Money Methodology

### A. The Flaw of Hard-Coded Price Constants
Hard-coding constants like ₹30,000 or ₹70,000 creates artificial price cliffs where a ₹71,000 laptop suddenly drops in score compared to a ₹69,000 laptop.

### B. The Calibrated Power-Law Formula
To model natural diminishing returns in economics (doubling price does not double utility):
1. Compute overall **Hardware Utility**:
   $$\text{Utility} = \frac{\text{score\_gaming} + \text{score\_programming} + \text{score\_video\_editing}}{3.0}$$
2. Compute **Price Efficiency** using power-law elasticity:
   $$\text{Price Ratio} = \frac{\text{price\_inr}}{50000.0}$$
   $$\text{Price Efficiency} = \frac{\text{Utility}}{(\text{Price Ratio})^{0.65}}$$
3. Normalize to 0–100 scale:
   $$\text{score\_value\_for\_money} = \min\left(99.0, \; \max(15.0, \; \text{Price Efficiency} \times 1.35)\right)$$

### C. Future Calibration on Final Dataset (2,000–3,000 Laptops)
This formula is currently labeled as an **initial heuristic**. Once the full 2,000–3,000 dataset is collected, we will calibrate the baseline denominator using the **empirical Pareto efficiency frontier** (identifying the top 10% performance-per-rupee laptops across each ₹10k price bracket).

---

## 8. Step-by-Step Viva Calculation Walkthroughs

During your college viva, you can manually trace any laptop's scores using these examples:

### Example 1: Lenovo LOQ 15ARP9 (Gaming Laptop — ₹1,04,290)
- **Input Specs**: Ryzen 7 7435HS (8C/16T, 4.5 GHz, Tier 3), RTX 4060 (8GB GDDR6, Tier 4), 24GB DDR5, 144Hz IPS (300 nits), 2.38 kg, 60 Wh, ₹1,04,290. All 8 specs present ($\text{Confidence} = 1.0$).

1. **Gaming Score**:
   - $\text{GPU Sub} = (4/5 \times 75) + (8/8 \times 25) = 60 + 25 = 85.0$
   - $\text{Hz Sub} = 95.0$ (144 Hz)
   - $\text{CPU Sub} = (3/5 \times 50) + (4.5/5 \times 50) = 30 + 45 = 75.0$
   - $\text{RAM Sub} = 50 + (16 \times 2.08) = 83.3$
   - $\text{score\_gaming} = (0.50 \times 85.0) + (0.15 \times 95.0) + (0.20 \times 75.0) + (0.15 \times 83.3) = \mathbf{84.2}$
2. **AI/ML Score**:
   - $\text{CUDA Sub} = 100.0$ (NVIDIA native)
   - $\text{VRAM Sub} = (8/16 \times 100) = 50.0$
   - $\text{RAM Sub} = (24/32 \times 100) = 75.0$
   - $\text{CPU Sub} = (8/16 \times 60) + (3/5 \times 40) = 30 + 24 = 54.0$
   - $\text{score\_aiml} = (0.35 \times 100) + (0.25 \times 50) + (0.20 \times 75) + (0.20 \times 54) = \mathbf{73.3}$
3. **Portability Score**:
   - $\text{Weight Sub} = 100 - ((2.38 - 1.1) / 1.7 \times 80) = 39.8$
   - $\text{Thickness Sub} = 100 - ((21.9 - 11) / 15 \times 70) = 49.1$
   - $\text{Battery Sub} = (60 / 70 \times 100) = 85.7$
   - $\text{score\_portability} = (0.50 \times 39.8) + (0.25 \times 49.1) + (0.25 \times 85.7) = \mathbf{53.6}$
4. **Value for Money**:
   - $\text{Utility} = (84.2 + 81.1 + 88.9) / 3 = 84.7$
   - $\text{Price Ratio} = 104290 / 50000 = 2.0858$
   - $\text{Price Efficiency} = 84.7 / (2.0858)^{0.65} = 84.7 / 1.611 = 52.57$
   - $\text{score\_value\_for\_money} = 52.57 \times 1.35 = \mathbf{70.9}$

---

### Example 2: Apple MacBook Air M4 (Ultraportable — ₹89,990)
- **Input Specs**: Apple M4 (10C/10T, 4.2 GHz, Tier 4), Apple 10-Core iGPU (0GB VRAM, Tier 1), 16GB RAM, 60Hz Retina (500 nits), 1.24 kg, 11.3 mm, 53.8 Wh, ₹89,990. ($\text{Confidence} = 1.0$).

1. **Portability Score**:
   - $\text{Weight Sub} = 100 - ((1.24 - 1.1) / 1.7 \times 80) = 93.4$
   - $\text{Thickness Sub} = 100 - ((11.3 - 11) / 15 \times 70) = 98.6$
   - $\text{Battery Sub} = (53.8 / 70 \times 100) = 76.9$
   - $\text{score\_portability} = (0.50 \times 93.4) + (0.25 \times 98.6) + (0.25 \times 76.9) = \mathbf{90.6}$ (Outstanding)
2. **Programming Score**:
   - $\text{CPU Sub} = (10/12 \times 50) + (4.2/4.8 \times 50) = 41.7 + 43.75 = 85.45$
   - $\text{RAM Sub} = 50 + (8 \times 2.08) = 66.7$
   - $\text{Storage Sub} = (256 / 1024 \times 70) + 30 = 47.5$
   - $\text{Display Sub} = (1664 / 1200 \times 60) + 20 = 80.0$
   - $\text{score\_programming} = (0.35 \times 85.45) + (0.35 \times 66.7) + (0.15 \times 47.5) + (0.15 \times 80.0) = \mathbf{72.4}$

---

### Example 3: Asus TUF Gaming A15 (Value Gaming — ₹55,990)
- **Input Specs**: Ryzen 7 7435HS, RTX 2050 (4GB GDDR6, Tier 2), 16GB RAM, 144Hz, ₹55,990.
- **Why it scores high on Value for Money (85.7)**:
  - Delivers a dedicated RTX GPU, 16GB RAM, and 144Hz screen for under ₹56,000.
  - $\text{Utility} = 68.3$, $\text{Price Ratio} = 1.1198$.
  - $\text{Price Efficiency} = 68.3 / (1.1198)^{0.65} = 68.3 / 1.076 = 63.48$.
  - $\text{score\_value\_for\_money} = 63.48 \times 1.35 = \mathbf{85.7}$ (Highest in current sample!).
