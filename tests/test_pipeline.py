import pytest
from pipeline.normalizer import (
    normalize_price, normalize_ram, normalize_storage,
    normalize_display, normalize_cpu, normalize_cores_and_threads,
    normalize_gpu, normalize_battery, normalize_weight, normalize_thickness
)
from pipeline.validator import validate_laptop_data
from pipeline.feature_engineer import compute_ml_features
from core.models import Laptop

def test_price_normalization():
    assert normalize_price(80999) == 80999.0
    assert normalize_price("₹80,999") == 80999.0
    assert normalize_price("Rs 1,04,290") == 104290.0
    assert normalize_price("₹80,999 (3% off)") == 80999.0
    assert normalize_price("₹44,990 15%") == 44990.0

def test_ram_normalization():
    ram_lpddr5 = normalize_ram("16 GB LPDDR5", "4800 MHz")
    assert ram_lpddr5["gb"] == 16
    assert ram_lpddr5["type"] == "LPDDR5"
    assert ram_lpddr5["speed_mhz"] == 4800

    ram_ddr5 = normalize_ram("16 GB DDR5", "5600 MHz")
    assert ram_ddr5["gb"] == 16
    assert ram_ddr5["type"] == "DDR5"
    assert ram_ddr5["speed_mhz"] == 5600

    ram_ddr4 = normalize_ram("8 GB DDR4", "3200 MHz")
    assert ram_ddr4["gb"] == 8
    assert ram_ddr4["type"] == "DDR4"
    assert ram_ddr4["speed_mhz"] == 3200

    ram_unified = normalize_ram("16 GB Unified Memory")
    assert ram_unified["gb"] == 16
    assert ram_unified["type"] == "Unified"

def test_storage_normalization():
    storage_info = normalize_storage("512 GB SSD")
    assert storage_info["gb"] == 512
    assert storage_info["type"] == "SSD"
    
    storage_tb = normalize_storage("1 TB PCIe NVMe SSD")
    assert storage_tb["gb"] == 1024
    assert storage_tb["type"] == "SSD"

def test_display_normalization():
    disp = normalize_display(
        size_text="15.6 inches",
        res_text="1920 x 1080 pixels",
        refresh_text="144 Hz",
        panel_text="IPS Screen",
        features_text="300nits , 100% sRGB, G-SYNC"
    )
    assert disp["screen_size_in"] == 15.6
    assert disp["resolution_width"] == 1920
    assert disp["resolution_height"] == 1080
    assert disp["refresh_rate_hz"] == 144
    assert disp["panel_type"] == "IPS"
    assert disp["brightness_nits"] == 300
    assert disp["srgb_pct"] == 100

def test_display_brightness_not_polluted_by_ntsc():
    # 45% NTSC should NOT be parsed as 45 nits
    disp = normalize_display(
        size_text="15.6 inches",
        res_text="1920 x 1080",
        refresh_text="60 Hz",
        panel_text="IPS",
        features_text="250 nits, 45% NTSC color gamut"
    )
    assert disp["brightness_nits"] == 250

def test_cpu_normalization():
    cpu = normalize_cpu(
        processor_text="13th Gen Intel Core i7 13620H",
        brand_raw="Intel",
        series_raw="Core i7",
        model_raw="13620H",
        generation_raw="13th Gen"
    )
    assert cpu["cpu_brand"] == "Intel"
    assert cpu["cpu_family"] == "Core i7 / Ryzen 7"
    assert cpu["cpu_generation"] == 13
    assert cpu["cpu_series_type"] == "H"
    assert cpu["is_high_perf"] is True
    assert cpu["cpu_tier"] == 4

def test_cores_and_threads():
    cores_info = normalize_cores_and_threads(
        cores_text="10 Cores (6P + 4E), 16 Threads",
        speed_text="6 x (Turbo Speed upto 4.9 GHz) Performance Cores"
    )
    assert cores_info["cores"] == 10
    assert cores_info["perf_cores"] == 6
    assert cores_info["eff_cores"] == 4
    assert cores_info["threads"] == 16
    assert cores_info["max_clock_ghz"] == 4.9

def test_gpu_normalization():
    # Dedicated RTX 4060 with explicit VRAM
    gpu_d = normalize_gpu("NVIDIA GeForce RTX 4060", "GDDR6 8 GB", "NVIDIA")
    assert gpu_d["gpu_brand"] == "NVIDIA"
    assert gpu_d["is_dedicated"] is True
    assert gpu_d["gpu_vram_gb"] == 8.0
    assert gpu_d["gpu_tier"] == 4

    # Dedicated RTX 4050 with unlisted VRAM (inferred as 6.0 GB)
    gpu_4050 = normalize_gpu("NVIDIA GeForce RTX 4050", None, "NVIDIA")
    assert gpu_4050["is_dedicated"] is True
    assert gpu_4050["gpu_vram_gb"] == 6.0
    assert gpu_4050["gpu_tier"] == 3

    # Integrated Intel
    gpu_i = normalize_gpu("Integrated Intel UHD Graphics", None, "Intel")
    assert gpu_i["gpu_brand"] == "Intel"
    assert gpu_i["is_dedicated"] is False
    assert gpu_i["gpu_vram_gb"] == 0.0
    assert gpu_i["gpu_tier"] == 0

def test_feature_engineering_scores():
    laptop = Laptop(
        id=1,
        brand="Lenovo",
        model_name="Lenovo LOQ 15 Gaming",
        os="Windows",
        price_inr=104290.0,
        mrp_inr=120000.0,
        cpu_brand="AMD",
        cpu_model="7435HS",
        cpu_cores=8,
        cpu_threads=16,
        cpu_max_clock_ghz=4.5,
        is_high_perf_cpu=True,
        is_dedicated_gpu=True,
        gpu_brand="NVIDIA",
        gpu_model="RTX 4060",
        gpu_vram_gb=8.0,
        ram_gb=24,
        storage_gb=512,
        storage_type="SSD",
        screen_size_in=15.6,
        resolution_width=1920,
        resolution_height=1080,
        refresh_rate_hz=144,
        brightness_nits=300,
        weight_kg=2.38,
        battery_wh=60.0
    )
    
    ml = compute_ml_features(laptop)
    assert ml.model_name == "Lenovo LOQ 15 Gaming"
    assert ml.has_dedicated_gpu is True
    assert ml.score_gaming > 75.0, f"Gaming score {ml.score_gaming} should be high for RTX 4060"
    assert ml.score_aiml > 70.0, f"AI/ML score {ml.score_aiml} should be high for NVIDIA 8GB VRAM"
    assert 0.0 <= ml.score_portability <= 100.0
    assert 0.0 <= ml.score_value_for_money <= 100.0
    assert ml.score_confidence == 1.0

def test_missing_values_and_confidence():
    # Laptop with missing battery and brightness
    laptop = Laptop(
        id=2,
        brand="HP",
        model_name="HP 15 Basic",
        price_inr=40000.0,
        cpu_cores=4,
        ram_gb=8,
        storage_gb=512,
        screen_size_in=15.6,
        weight_kg=1.75,
        battery_wh=None,       # Missing
        brightness_nits=None   # Missing
    )
    ml = compute_ml_features(laptop)
    # Confidence should reflect 6 out of 8 specs present
    assert ml.score_confidence == 0.75
    # Portability must NOT collapse to 0 just because battery is missing
    assert ml.score_portability > 40.0

def test_validator_rules():
    warnings = validate_laptop_data({
        "price_inr": 2000, # too low
        "ram_gb": 7,       # unusual
        "cpu_cores": 1     # too low
    })
    assert len(warnings) == 3

def test_store_extraction_and_features():
    import json
    from collectors.smartprix import SmartprixCollector

    html_snippet = """
    <html>
      <head><script type="application/ld+json">{"@type": "Product", "name": "Test Book Pro", "brand": "TestBrand", "offers": {"price": "85000"}}</script></head>
      <body>
        <h1>Test Book Pro</h1>
        <div class="sm-box-item sm-pc-item">
          <img alt="amazon" src="/amazon.png" />
          <span class="price">₹82,490</span>
          <a href="https://l.smartprix.com/l?k=amazon_deal">Buy</a>
        </div>
        <div class="sm-box-item sm-pc-item">
          <img alt="croma" src="/croma.png" />
          <span class="price">₹79,990</span>
          <a href="https://l.smartprix.com/l?k=croma_deal">Buy</a>
        </div>
      </body>
    </html>
    """
    collector = SmartprixCollector()
    raw = collector.extract_raw_fields(html_snippet, None)
    
    # 1. Verify collector extracted clean store links & details
    assert "amazon" in raw["shop_links"]
    assert "croma" in raw["shop_links"]
    assert raw["shop_links"]["amazon"] == "https://l.smartprix.com/l?k=amazon_deal"
    assert raw["shop_links"]["croma"] == "https://l.smartprix.com/l?k=croma_deal"
    assert raw["min_store_price"] == 79990.0
    assert raw["best_store"] == "croma"

    # 2. Verify ML feature engineering integration
    laptop = Laptop(
        id=10,
        model_name="Test Book Pro",
        brand="TestBrand",
        price_inr=85000.0,
        best_store=raw["best_store"],
        shop_links=raw["shop_links"],
        cpu_cores=8,
        ram_gb=16,
        storage_gb=512,
        screen_size_in=14.0,
        weight_kg=1.4,
        battery_wh=50.0,
        brightness_nits=300
    )
    ml = compute_ml_features(laptop)
    assert ml.store_count == 2
    assert ml.has_amazon is True
    assert ml.has_croma is True
    assert ml.has_flipkart is False
    assert ml.best_store == "croma"
    
    decoded_shops = json.loads(ml.shop_links)
    assert decoded_shops["amazon"] == "https://l.smartprix.com/l?k=amazon_deal"
    assert decoded_shops["croma"] == "https://l.smartprix.com/l?k=croma_deal"

def test_cpu_tier_and_vram_in_ml_features():
    # Core i7 with model-only cpu_model string
    l_i7 = Laptop(
        id=1,
        brand="Lenovo",
        model_name="Lenovo IdeaPad Slim 3 83K100CJIN Laptop (13th Gen Core i7/ 16GB)",
        cpu_family="Core i7 / Ryzen 7",
        cpu_model="13620H",
        cpu_cores=10,
        ram_gb=16,
        storage_gb=512,
        price_inr=80999.0
    )
    ml_i7 = compute_ml_features(l_i7)
    assert ml_i7.cpu_tier == 4, f"Core i7 should be Tier 4, got {ml_i7.cpu_tier}"

    # Core i3 with model-only string
    l_i3 = Laptop(
        id=2,
        brand="HP",
        model_name="HP 15-fd0573TU Laptop (13th Gen Core i3/ 8GB)",
        cpu_family="Core i3 / Ryzen 3",
        cpu_model="1315U",
        cpu_cores=6,
        ram_gb=8,
        storage_gb=512,
        price_inr=44990.0
    )
    ml_i3 = compute_ml_features(l_i3)
    assert ml_i3.cpu_tier == 2, f"Core i3 should be Tier 2, got {ml_i3.cpu_tier}"

def test_year_filter():
    from pipeline.year_filter import is_laptop_2022_or_newer
    
    # 2022+ Valid laptops
    assert is_laptop_2022_or_newer("Lenovo IdeaPad 13th Gen", "13620H", "Intel", cpu_generation=13)[0] is True
    assert is_laptop_2022_or_newer("Asus Vivobook 12th Gen", "12500H", "Intel", cpu_generation=12)[0] is True
    assert is_laptop_2022_or_newer("Asus Core Ultra 7", "255H", "Intel")[0] is True
    assert is_laptop_2022_or_newer("Lenovo LOQ Gaming", "7435HS", "AMD", cpu_generation=7)[0] is True
    assert is_laptop_2022_or_newer("Apple MacBook Air M4", "M4", "Apple")[0] is True
    assert is_laptop_2022_or_newer("Dell Inspiron", "1334U", "Intel", cpu_generation=13)[0] is True
    assert is_laptop_2022_or_newer("Asus Core 5 120U", "120U", "Intel")[0] is True
    assert is_laptop_2022_or_newer("Acer N100 Laptop", "N100", "Intel")[0] is True

    # Pre-2022 Obsolete laptops (should be rejected)
    assert is_laptop_2022_or_newer("Asus VivoBook 15 2021 X515JA", "1005G1", "Intel", cpu_generation=10)[0] is False
    assert is_laptop_2022_or_newer("HP 11th Gen Laptop", "1135G7", "Intel", cpu_generation=11)[0] is False
    assert is_laptop_2022_or_newer("Budget Celeron Laptop", "N4020", "Intel")[0] is False
    assert is_laptop_2022_or_newer("Old Ryzen Laptop", "3500U", "AMD")[0] is False
    assert is_laptop_2022_or_newer("Ryzen 4000 Laptop", "4500U", "AMD")[0] is False
    assert is_laptop_2022_or_newer("Apple MacBook Air M1 2020", "M1", "Apple")[0] is False


