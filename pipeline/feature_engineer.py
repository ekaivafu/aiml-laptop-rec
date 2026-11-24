import math
import json
import re
from typing import Dict, Any, Optional, Tuple
from core.models import Laptop, LaptopMLFeature

def compute_ml_features(laptop: Laptop) -> LaptopMLFeature:
    """
    Transforms a normalized Laptop catalog record into a sanitized, numeric ML feature row
    with 7 objective use-case benchmark scores and a score confidence indicator.
    
    NOTE: These 7 scores are domain-knowledge/heuristic engineered features,
    NOT the machine-learning model itself. Downstream ML models (e.g. KNN, LightGBM)
    can utilize both the raw normalized features and these engineered scores.
    """
    # -------------------------------------------------------------
    # 1. SPECIFICATION COMPLETENESS & SCORE CONFIDENCE
    # -------------------------------------------------------------
    # Check 8 core specifications to determine data completeness
    essential_specs = {
        "price": laptop.price_inr is not None and laptop.price_inr > 0,
        "cpu": laptop.cpu_cores is not None and laptop.cpu_cores > 0,
        "ram": laptop.ram_gb is not None and laptop.ram_gb > 0,
        "storage": laptop.storage_gb is not None and laptop.storage_gb > 0,
        "screen": laptop.screen_size_in is not None and laptop.screen_size_in > 0,
        "weight": laptop.weight_kg is not None and laptop.weight_kg > 0,
        "battery": laptop.battery_wh is not None and laptop.battery_wh > 0,
        "brightness": laptop.brightness_nits is not None and laptop.brightness_nits > 0
    }
    
    available_count = sum(1 for v in essential_specs.values() if v)
    score_confidence = round(available_count / float(len(essential_specs)), 2)

    # -------------------------------------------------------------
    # 2. FEATURE EXTRACTION & NEUTRAL IMPUTATION (NO ZERO PENALTIES)
    # -------------------------------------------------------------
    price = laptop.price_inr or 55000.0
    model_name = laptop.model_name or "Unknown Laptop"
    brand = laptop.brand or (model_name.split()[0] if model_name else "Unknown")
    os_name = laptop.os or "Windows"
    cpu_brand = laptop.cpu_brand or "Intel"
    
    # CPU Specs
    cores = laptop.cpu_cores or 8
    threads = laptop.cpu_threads or (cores * 2 if cores <= 8 else cores)
    max_ghz = laptop.cpu_max_clock_ghz or 4.2
    is_high_perf = bool(laptop.is_high_perf_cpu)
    
    # Project-Defined Normalized CPU Performance Tier (1 to 5)
    # Based strictly on CPU family, series, and model name (no invented benchmark)
    cpu_tier = 3
    combined_cpu = f"{laptop.cpu_family or ''} {laptop.model_name or ''} {laptop.cpu_model or ''}".lower()
    if any(k in combined_cpu for k in ["ultra 9", "core i9", "i9-", "ryzen 9", "m4 max", "m3 max", "m2 max"]):
        cpu_tier = 5
    elif any(k in combined_cpu for k in ["ultra 7", "core i7", "i7-", "ryzen 7", "m4 pro", "m3 pro", "m2 pro", "m4"]):
        cpu_tier = 4
    elif any(k in combined_cpu for k in ["ultra 5", "core i5", "i5-", "ryzen 5", "m3", "m2"]):
        cpu_tier = 3
    elif any(k in combined_cpu for k in ["core i3", "i3-", "ryzen 3", "m1"]):
        cpu_tier = 2
    elif any(k in combined_cpu for k in ["celeron", "pentium", "athlon"]):
        cpu_tier = 1

    perf_cores = cores
    if cores >= 10:
        perf_cores = max(2, cores - 4)

    # GPU Specs
    has_dgpu = bool(laptop.is_dedicated_gpu)
    gpu_brand = laptop.gpu_brand or ("NVIDIA" if has_dgpu else "Intel")
    gpu_str = (laptop.gpu_model or "").lower()
    
    # VRAM handling: 0.0 is genuine for integrated GPUs. 
    # For dedicated GPUs with unlisted VRAM, infer standard capacity or use 4.0 GB conservative fallback.
    if has_dgpu:
        if laptop.gpu_vram_gb is not None and laptop.gpu_vram_gb > 0:
            vram = float(laptop.gpu_vram_gb)
        elif re.search(r'4090|5090', gpu_str):
            vram = 16.0
        elif re.search(r'4080|5080', gpu_str):
            vram = 12.0
        elif re.search(r'(?:4070|4060|5060|5070|3080|3070)', gpu_str):
            vram = 8.0
        elif re.search(r'(?:4050|3060|2060)', gpu_str):
            vram = 6.0
        elif re.search(r'(?:3050|2050)|1650|6500', gpu_str):
            vram = 4.0
        else:
            vram = 4.0
    else:
        vram = 0.0
    
    # Project-Defined Normalized GPU Performance Tier (0 to 5)
    gpu_tier = 0
    if has_dgpu:
        if vram >= 12 or any(k in gpu_str for k in ["4080", "4090", "5080", "5090"]):
            gpu_tier = 5
        elif vram >= 8 or any(k in gpu_str for k in ["4060", "4070", "5060", "5070", "3080", "3070"]):
            gpu_tier = 4
        elif vram >= 6 or any(k in gpu_str for k in ["4050", "3060", "2060"]):
            gpu_tier = 3
        elif vram >= 4 or any(k in gpu_str for k in ["3050", "2050", "1650", "6500"]):
            gpu_tier = 2
        else:
            gpu_tier = 2
    elif any(k in gpu_str for k in ["iris", "radeon 7", "radeon 6", "radeon 8", "intel arc", "apple"]):
        gpu_tier = 1
    elif "ultra" in (laptop.cpu_family or "").lower() or "ultra" in (laptop.model_name or "").lower():
        gpu_tier = 1

    # RAM & Storage Specs
    ram = laptop.ram_gb or 16
    ram_type = laptop.ram_type or ("DDR5" if "DDR5" in str(laptop.raw_specs) else "DDR4")
    ram_speed = laptop.ram_speed_mhz or (4800 if "5" in ram_type else 3200)
    storage = laptop.storage_gb or 512
    is_ssd = "hdd" not in (laptop.storage_type or "").lower()

    # Display Specs
    screen_size = laptop.screen_size_in or 15.6
    res_w = laptop.resolution_width or 1920
    res_h = laptop.resolution_height or 1080
    refresh_rate = laptop.refresh_rate_hz or 60
    is_oled = "oled" in (laptop.panel_type or "").lower() or "oled" in str(laptop.display_features or "").lower()
    brightness = laptop.brightness_nits or (300 if not is_oled else 400)
    touchscreen = bool(laptop.touchscreen)
    anti_glare = bool(laptop.anti_glare)

    # Mobility Specs
    weight = laptop.weight_kg or (2.2 if has_dgpu else 1.6)
    thickness = laptop.thickness_mm or (22.0 if has_dgpu else 17.5)
    battery = laptop.battery_wh or (60.0 if has_dgpu else 48.0)

    # -------------------------------------------------------------
    # 3. DOMAIN-HEURISTIC SCORING WITH DIMINISHING RETURNS
    # -------------------------------------------------------------

    # -------------------------------------------------------------
    # SCORE 1: GAMING (Weights: GPU 50%, CPU 20%, RAM 15%, Refresh Rate 15%)
    # -------------------------------------------------------------
    # GPU Sub-score (50%): Tier (0-5) and VRAM scaling
    gpu_game_sub = min(100.0, (gpu_tier / 5.0) * 75.0 + (min(vram, 8.0) / 8.0) * 25.0)
    
    # Display Hz Sub-score (15%): Smooth curve (60Hz=45, 90Hz=65, 120Hz=85, 144Hz=95, 165Hz+=100)
    if refresh_rate >= 144:
        hz_sub = min(100.0, 95.0 + (refresh_rate - 144) * 0.15)
    elif refresh_rate >= 120:
        hz_sub = 85.0 + (refresh_rate - 120) * 0.41
    elif refresh_rate >= 90:
        hz_sub = 65.0 + (refresh_rate - 90) * 0.66
    else:
        hz_sub = 45.0
        
    # CPU Sub-score (20%): Tier and single-core clock
    cpu_game_sub = min(100.0, (cpu_tier / 5.0) * 50.0 + (min(max_ghz, 5.0) / 5.0) * 50.0)
    
    # RAM Sub-score (15%): Diminishing returns (8GB=50, 16GB=85, 24GB=95, 32GB=100)
    ram_game_sub = min(100.0, 50.0 + (min(ram, 32) - 8) * (50.0 / 24.0)) if ram >= 8 else (ram / 8.0) * 50.0
    
    score_gaming = round(0.50 * gpu_game_sub + 0.15 * hz_sub + 0.20 * cpu_game_sub + 0.15 * ram_game_sub, 1)

    # -------------------------------------------------------------
    # SCORE 2: AI / ML (Weights: GPU/CUDA 35%, VRAM 25%, RAM 20%, CPU 20%)
    # -------------------------------------------------------------
    # CUDA Platform Ecosystem Sub-score (35%)
    is_apple_silicon = "apple" in brand.lower() or "apple" in gpu_brand.lower() or "apple" in cpu_brand.lower()
    if "nvidia" in gpu_brand.lower():
        cuda_sub = 100.0  # Native PyTorch / TensorFlow CUDA
    elif is_apple_silicon:
        cuda_sub = 60.0   # MPS / MLX acceleration on unified memory
    else:
        cuda_sub = 15.0   # CPU / OpenVINO basic fallback only
        
    # VRAM Sub-score (25%): 4GB=40, 6GB=65, 8GB=85, 12GB=95, 16GB=100
    if has_dgpu:
        vram_ml_sub = min(100.0, (min(vram, 16.0) / 16.0) * 100.0)
    elif is_apple_silicon:
        # On Apple Silicon, unified memory acts as shared high-bandwidth VRAM for LLMs/PyTorch
        effective_vram = min(float(ram), 16.0)
        vram_ml_sub = min(100.0, (effective_vram / 16.0) * 85.0)
    else:
        vram_ml_sub = 10.0
    
    # System RAM Sub-score (20%): Large dataset capacity (target 32GB)
    ram_ml_sub = min(100.0, (min(ram, 32) / 32.0) * 100.0)
    
    # CPU Multi-core Sub-score (20%)
    cpu_ml_sub = min(100.0, (min(cores, 16) / 16.0) * 60.0 + (cpu_tier / 5.0) * 40.0)
    
    score_aiml = round(0.35 * cuda_sub + 0.25 * vram_ml_sub + 0.20 * ram_ml_sub + 0.20 * cpu_ml_sub, 1)

    # -------------------------------------------------------------
    # SCORE 3: VIDEO EDITING (Weights: GPU 30%, CPU 30%, Display 20%, RAM 20%)
    # -------------------------------------------------------------
    # GPU Hardware Encoding Sub-score (30%)
    gpu_edit_sub = min(100.0, (gpu_tier / 4.0) * 70.0 + (min(vram, 8.0) / 8.0) * 30.0)
    
    # CPU Multi-threaded Rendering Sub-score (30%)
    cpu_edit_sub = min(100.0, (min(threads, 16) / 16.0) * 60.0 + (cpu_tier / 5.0) * 40.0)
    
    # Display Quality Sub-score (20%)
    disp_sub = min(100.0, (min(res_w, 2560) / 2560.0) * 50.0 + (25.0 if is_oled else 12.0) + (min(brightness, 400) / 400.0) * 25.0)
    
    # RAM Sub-score (20%): 16GB target
    ram_edit_sub = min(100.0, (min(ram, 32) / 16.0) * 80.0 + (20.0 if ram >= 24 else 0.0))
    
    score_video_editing = round(0.30 * gpu_edit_sub + 0.30 * cpu_edit_sub + 0.20 * disp_sub + 0.20 * ram_edit_sub, 1)

    # -------------------------------------------------------------
    # SCORE 4: PROGRAMMING (Weights: CPU 35%, RAM 35%, Storage 15%, Ergonomics 15%)
    # -------------------------------------------------------------
    # CPU Compilation Sub-score (35%)
    cpu_prog_sub = min(100.0, (min(cores, 12) / 12.0) * 50.0 + (min(max_ghz, 4.8) / 4.8) * 50.0)
    
    # RAM Sub-score (35%): Heavy Docker/IDE multitasking
    ram_prog_sub = min(100.0, 50.0 + (min(ram, 32) - 8) * (50.0 / 24.0)) if ram >= 8 else (ram / 8.0) * 50.0
    
    # Storage Sub-score (15%)
    storage_sub = min(100.0, (min(storage, 1024) / 1024.0) * 70.0 + (30.0 if is_ssd else 0.0))
    
    # Display Ergonomics Sub-score (15%): Vertical resolution & anti-glare
    disp_prog_sub = min(100.0, (min(res_h, 1200) / 1200.0) * 60.0 + (40.0 if anti_glare else 20.0))
    
    score_programming = round(0.35 * cpu_prog_sub + 0.35 * ram_prog_sub + 0.15 * storage_sub + 0.15 * disp_prog_sub, 1)

    # -------------------------------------------------------------
    # SCORE 5: PORTABILITY (Weights: Weight 50%, Thickness 25%, Battery 25%)
    # Dynamic sub-weight redistribution if battery or thickness is unlisted
    # -------------------------------------------------------------
    # Weight Sub-score: Linear decline from 1.1kg (100) to 2.8kg (20)
    weight_sub = max(10.0, min(100.0, 100.0 - ((weight - 1.1) / 1.7) * 80.0))
    
    # Thickness Sub-score: 11mm (100) to 26mm (30)
    thick_sub = max(15.0, min(100.0, 100.0 - ((thickness - 11.0) / 15.0) * 70.0))
    
    # Battery Sub-score: 35Wh (35) to 80Wh (100)
    bat_sub = max(20.0, min(100.0, (battery / 70.0) * 100.0))
    
    # Check if battery was genuinely reported or imputed
    if essential_specs["battery"] and essential_specs["weight"]:
        score_portability = round(0.50 * weight_sub + 0.25 * thick_sub + 0.25 * bat_sub, 1)
    else:
        # Dynamic weight redistribution: Weight gets 67%, Thickness gets 33%
        score_portability = round(0.67 * weight_sub + 0.33 * thick_sub, 1)

    # -------------------------------------------------------------
    # SCORE 6: STUDENT / OFFICE (Weights: Portability 35%, Affordability 35%, Battery 15%, Display 15%)
    # -------------------------------------------------------------
    # Affordability Sub-score (35%): Smooth curve favoring accessible pricing in India (Rs. 25k to 70k)
    # Beyond Rs. 80,000 affordability gently tapers down with diminishing utility
    afford_sub = max(10.0, min(100.0, 100.0 - ((price - 25000.0) / 85000.0) * 75.0))
    
    score_student_office = round(0.35 * score_portability + 0.35 * afford_sub + 0.15 * bat_sub + 0.15 * disp_sub, 1)

    # Store & Market Availability Features
    raw_shops = getattr(laptop, "shop_links", None)
    if isinstance(raw_shops, str):
        try:
            shop_dict = json.loads(raw_shops)
        except Exception:
            shop_dict = {}
    elif isinstance(raw_shops, dict):
        shop_dict = raw_shops
    else:
        shop_dict = {}

    store_count = max(1, len(shop_dict))
    shop_keys = [k.lower() for k in shop_dict.keys()]
    has_amazon = "amazon" in shop_keys
    has_croma = "croma" in shop_keys
    has_flipkart = "flipkart" in shop_keys
    best_store = getattr(laptop, "best_store", None) or ("smartprix" if not shop_keys else shop_keys[0])
    
    shop_links_json = json.dumps(shop_dict)

    # -------------------------------------------------------------
    # 7. SCORE: VALUE FOR MONEY (0.0 - 100.0)
    # -------------------------------------------------------------
    # Evaluates overall hardware capability against market pricing.
    hardware_utility = (
        (score_gaming * 0.20) +
        (score_aiml * 0.15) +
        (score_video_editing * 0.15) +
        (score_programming * 0.20) +
        (score_student_office * 0.15) +
        (score_portability * 0.15)
    )
    
    # Calibrated Price Efficiency using market price:
    # A laptop receives higher value when it provides more useful hardware capability per Rupee.
    # We apply power-law elasticity (price ** 0.65) to model diminishing returns on expenditure.
    price_ratio = max(20000.0, price) / 50000.0
    price_efficiency = hardware_utility / (price_ratio ** 0.65)
    score_value_for_money = round(max(15.0, min(99.0, price_efficiency * 1.35)), 1)

    return LaptopMLFeature(
        laptop_id=laptop.id,
        model_name=model_name,
        brand=brand,
        price_inr=price,
        best_store=best_store,
        store_count=store_count,
        has_amazon=has_amazon,
        has_croma=has_croma,
        has_flipkart=has_flipkart,
        shop_links=shop_links_json,
        os=os_name,
        cpu_brand=cpu_brand,
        cpu_tier=cpu_tier,
        cpu_cores=cores,
        cpu_threads=threads,
        cpu_perf_cores=perf_cores,
        cpu_max_ghz=max_ghz,
        is_high_perf_cpu=is_high_perf,
        has_dedicated_gpu=has_dgpu,
        gpu_brand=gpu_brand,
        gpu_tier=gpu_tier,
        gpu_vram_gb=vram,
        ram_gb=ram,
        ram_type=ram_type,
        ram_speed_mhz=ram_speed,
        storage_gb=storage,
        is_ssd=is_ssd,
        screen_size_in=screen_size,
        resolution_width=res_w,
        resolution_height=res_h,
        refresh_rate_hz=refresh_rate,
        is_oled=is_oled,
        brightness_nits=brightness,
        is_touchscreen=touchscreen,
        is_anti_glare=anti_glare,
        weight_kg=weight,
        thickness_mm=thickness,
        battery_wh=battery,
        score_gaming=score_gaming,
        score_aiml=score_aiml,
        score_video_editing=score_video_editing,
        score_programming=score_programming,
        score_student_office=score_student_office,
        score_portability=score_portability,
        score_value_for_money=score_value_for_money,
        score_confidence=score_confidence
    )
