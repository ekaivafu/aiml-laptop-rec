import re
from typing import Optional, Dict, Any, Tuple

def clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned = text.strip()
    return cleaned if cleaned else None

def extract_integer(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    try:
        match = re.search(r'\b\d+\b', text)
        if match:
            return int(match.group())
        return None
    except Exception:
        return None

def extract_float(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    text = text.replace(',', '')
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def normalize_price(price_val: Any) -> Optional[float]:
    if price_val is None:
        return None
    if isinstance(price_val, (int, float)):
        return float(price_val)
    text = str(price_val).strip()
    # Strip any percentages or discount mentions first
    text = re.sub(r'\s*\d+%\s*(?:off)?', '', text, flags=re.IGNORECASE)
    text = text.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
    match = re.search(r'(\d+(?:\.\d+)?)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def normalize_thickness(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    # e.g., "359.3 x 235 x 17.9 mm" -> 17.9
    match = re.search(r'x\s*([\d\.]+)\s*mm', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    match_single = re.search(r'([\d\.]+)\s*mm', text, re.IGNORECASE)
    if match_single:
        return float(match_single.group(1))
    return extract_float(text)

def normalize_weight(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    match_kg = re.search(r'(\d+(?:\.\d+)?)\s*kg', text, re.IGNORECASE)
    if match_kg:
        return float(match_kg.group(1))
    match_g = re.search(r'(\d+(?:\.\d+)?)\s*g\b', text, re.IGNORECASE)
    if match_g and 'kg' not in text.lower():
        return round(float(match_g.group(1)) / 1000.0, 2)
    return extract_float(text)

def normalize_boolean(text: Optional[str]) -> Optional[bool]:
    if text is None:
        return None
    if isinstance(text, bool):
        return text
    text_clean = str(text).lower().strip()
    if text_clean in ['yes', 'true', '1', 'available', 'supported']:
        return True
    if text_clean in ['no', 'false', '0', 'not available', 'cross']:
        return False
    return None

def normalize_ram(ram_text: Optional[str], bus_speed_text: Optional[str] = None) -> Dict[str, Any]:
    result = {"gb": None, "type": None, "speed_mhz": None}
    combined = f"{ram_text or ''} {bus_speed_text or ''}".upper()
    if not combined.strip():
        return result
        
    gb_match = re.search(r'(\d+)\s*(?:GB|MB)', combined)
    if gb_match:
        result["gb"] = int(gb_match.group(1))
        
    type_match = re.search(r'((?:LP)?DDR\d[X]?|UNIFIED)', combined)
    if type_match:
        matched_val = type_match.group(1)
        result["type"] = "Unified" if matched_val == "UNIFIED" else matched_val
        
    speed_match = re.search(r'(\d{4})\s*MHZ', combined)
    if speed_match:
        result["speed_mhz"] = int(speed_match.group(1))
        
    return result

def normalize_storage(storage_text: Optional[str]) -> Dict[str, Any]:
    result = {"gb": None, "type": None}
    if not storage_text:
        return result
    text = storage_text.upper()
    
    gb_match = re.search(r'(\d+)\s*GB', text)
    tb_match = re.search(r'(\d+(?:\.\d+)?)\s*TB', text)
    if gb_match:
        result["gb"] = int(gb_match.group(1))
    elif tb_match:
        result["gb"] = int(float(tb_match.group(1)) * 1024)
        
    if "SSD" in text or "NVME" in text:
        result["type"] = "SSD"
    elif "EMMC" in text:
        result["type"] = "eMMC"
    elif "HDD" in text:
        result["type"] = "HDD"
    else:
        result["type"] = "SSD" # Default modern laptop storage
        
    return result

def normalize_display(
    size_text: Optional[str], 
    res_text: Optional[str], 
    refresh_text: Optional[str] = None, 
    panel_text: Optional[str] = None, 
    features_text: Optional[str] = None
) -> Dict[str, Any]:
    result = {
        "screen_size_in": None,
        "resolution_width": None,
        "resolution_height": None,
        "resolution_str": None,
        "refresh_rate_hz": 60,
        "panel_type": None,
        "brightness_nits": None,
        "srgb_pct": None,
        "is_oled": False
    }
    
    # Size
    if size_text:
        size_match = re.search(r'(\d+(?:\.\d+)?)', str(size_text))
        if size_match:
            result["screen_size_in"] = float(size_match.group(1))
            
    # Resolution
    if res_text:
        res_match = re.search(r'(\d{3,4})\s*[xX*]\s*(\d{3,4})', res_text)
        if res_match:
            w, h = int(res_match.group(1)), int(res_match.group(2))
            result["resolution_width"] = w
            result["resolution_height"] = h
            result["resolution_str"] = f"{w} x {h}"
            
    # Refresh Rate
    combined_refresh = f"{refresh_text or ''} {features_text or ''}"
    hz_match = re.search(r'(\d{2,3})\s*Hz\b', combined_refresh, re.IGNORECASE)
    if hz_match:
        result["refresh_rate_hz"] = int(hz_match.group(1))
    elif refresh_text:
        direct_hz = extract_integer(refresh_text)
        if direct_hz and 40 <= direct_hz <= 360:
            result["refresh_rate_hz"] = direct_hz

    # Panel Type & OLED
    combined_panel = f"{panel_text or ''} {features_text or ''}".upper()
    if "OLED" in combined_panel:
        result["panel_type"] = "OLED"
        result["is_oled"] = True
    elif "IPS" in combined_panel:
        result["panel_type"] = "IPS"
    elif "VA" in combined_panel or "WVA" in combined_panel:
        result["panel_type"] = "VA"
    elif "TN" in combined_panel:
        result["panel_type"] = "TN"

    # Brightness (Strictly match \d+\s*nits, NOT % or angles)
    if features_text:
        nits_match = re.search(r'(\d{3,4})\s*nits\b', features_text, re.IGNORECASE)
        if nits_match:
            result["brightness_nits"] = int(nits_match.group(1))
        # sRGB
        srgb_match = re.search(r'(\d{2,3})%\s*sRGB', features_text, re.IGNORECASE)
        if srgb_match:
            result["srgb_pct"] = int(srgb_match.group(1))
            
    return result

def normalize_cpu(
    processor_text: Optional[str],
    brand_raw: Optional[str] = None,
    series_raw: Optional[str] = None,
    model_raw: Optional[str] = None,
    generation_raw: Optional[str] = None
) -> Dict[str, Any]:
    result = {
        "cpu_brand": None,
        "cpu_family": None,
        "cpu_model": None,
        "cpu_generation": None,
        "cpu_series_type": None,
        "is_high_perf": False,
        "cpu_tier": 2
    }
    raw = f"{processor_text or ''} {brand_raw or ''} {series_raw or ''} {model_raw or ''}".strip()
    if not raw:
        return result
        
    raw_lower = raw.lower()
    
    # Brand
    if "intel" in raw_lower:
        result["cpu_brand"] = "Intel"
    elif "amd" in raw_lower or "ryzen" in raw_lower:
        result["cpu_brand"] = "AMD"
    elif "apple" in raw_lower or re.search(r'\bm[1234]\b', raw_lower):
        result["cpu_brand"] = "Apple"
    elif "snapdragon" in raw_lower or "qualcomm" in raw_lower:
        result["cpu_brand"] = "Qualcomm"
        
    # Family & Tier
    if "core ultra 9" in raw_lower or "core i9" in raw_lower or "ryzen 9" in raw_lower or "m4 pro" in raw_lower or "m4 max" in raw_lower:
        result["cpu_family"] = "Core i9 / Ryzen 9"
        result["cpu_tier"] = 5
    elif "core ultra 7" in raw_lower or "core i7" in raw_lower or "ryzen 7" in raw_lower or "m4" in raw_lower or "m3 pro" in raw_lower:
        result["cpu_family"] = "Core i7 / Ryzen 7"
        result["cpu_tier"] = 4
    elif "core ultra 5" in raw_lower or "core i5" in raw_lower or "ryzen 5" in raw_lower or "m2" in raw_lower or "m3" in raw_lower:
        result["cpu_family"] = "Core i5 / Ryzen 5"
        result["cpu_tier"] = 3
    elif "core i3" in raw_lower or "ryzen 3" in raw_lower or "m1" in raw_lower:
        result["cpu_family"] = "Core i3 / Ryzen 3"
        result["cpu_tier"] = 2
    elif "celeron" in raw_lower or "pentium" in raw_lower or "athlon" in raw_lower:
        result["cpu_family"] = "Entry / Celeron"
        result["cpu_tier"] = 1

    # Generation
    gen_match = re.search(r'(\d+)(?:th|rd|st|nd)\s*Gen', raw, re.IGNORECASE)
    if gen_match:
        result["cpu_generation"] = int(gen_match.group(1))
    elif generation_raw:
        gen_int = extract_integer(generation_raw)
        if gen_int:
            result["cpu_generation"] = gen_int
            
    # Series suffix (H, HX, HS, U, P)
    suffix_match = re.search(r'(\d{4,5})\s*([Hh][Xx]?|[Hh][Ss]|[Hh]|[Uu]|[Pp])\b', raw)
    if suffix_match:
        suffix = suffix_match.group(2).upper()
        result["cpu_series_type"] = suffix
        if suffix in ['H', 'HX', 'HS']:
            result["is_high_perf"] = True
    elif "ultra" in raw_lower and ("h" in raw_lower or "hx" in raw_lower):
        result["is_high_perf"] = True
        result["cpu_series_type"] = "H"

    # CPU Model
    result["cpu_model"] = model_raw or processor_text
    return result

def normalize_cores_and_threads(cores_text: Optional[str], speed_text: Optional[str] = None) -> Dict[str, Any]:
    result = {"cores": None, "perf_cores": None, "eff_cores": None, "threads": None, "max_clock_ghz": None}
    if not cores_text and not speed_text:
        return result
        
    c_text = (cores_text or "").lower()
    
    # Cores
    num_map = {'single': 1, 'dual': 2, 'quad': 4, 'hexa': 6, 'octa': 8, 'deca': 10, 'dodeca': 12}
    for word, n in num_map.items():
        if word in c_text:
            result["cores"] = n
            break
    if not result["cores"]:
        m = re.search(r'(\d+)\s*cores?', c_text)
        if m:
            result["cores"] = int(m.group(1))
            
    # P-Cores & E-Cores (e.g. 6P + 4E)
    pe_match = re.search(r'(\d+)\s*p\s*\+\s*(\d+)\s*e', c_text)
    if pe_match:
        result["perf_cores"] = int(pe_match.group(1))
        result["eff_cores"] = int(pe_match.group(2))
    elif result["cores"]:
        result["perf_cores"] = result["cores"]
        result["eff_cores"] = 0
        
    # Threads
    th_match = re.search(r'(\d+)\s*threads?', c_text)
    if th_match:
        result["threads"] = int(th_match.group(1))
    elif result["cores"]:
        result["threads"] = result["cores"] * 2 if result["cores"] <= 8 else result["cores"]

    # Max Clock Ghz
    combined_speed = f"{speed_text or ''} {cores_text or ''}"
    turbo_match = re.search(r'upto\s*([\d\.]+)\s*GHz', combined_speed, re.IGNORECASE)
    if turbo_match:
        result["max_clock_ghz"] = float(turbo_match.group(1))
    else:
        ghz_match = re.search(r'([\d\.]+)\s*GHz', combined_speed, re.IGNORECASE)
        if ghz_match:
            result["max_clock_ghz"] = float(ghz_match.group(1))
            
    return result

def normalize_gpu(gpu_text: Optional[str], vram_text: Optional[str] = None, brand_raw: Optional[str] = None) -> Dict[str, Any]:
    result = {
        "gpu_model": gpu_text,
        "gpu_brand": None,
        "is_dedicated": False,
        "gpu_vram_gb": 0.0,
        "gpu_tier": 0
    }
    combined = f"{gpu_text or ''} {brand_raw or ''} {vram_text or ''}".strip()
    if not combined:
        return result
        
    c_lower = combined.lower()
    
    # Brand
    if "nvidia" in c_lower or "geforce" in c_lower or "rtx" in c_lower or "gtx" in c_lower:
        result["gpu_brand"] = "NVIDIA"
        result["is_dedicated"] = True
    elif "amd" in c_lower or "radeon" in c_lower:
        result["gpu_brand"] = "AMD"
        if "rx" in c_lower:
            result["is_dedicated"] = True
    elif "apple" in c_lower:
        result["gpu_brand"] = "Apple"
    elif "intel" in c_lower:
        result["gpu_brand"] = "Intel"
        if "arc a" in c_lower:
            result["is_dedicated"] = True

    # VRAM
    if vram_text:
        v_match = re.search(r'(\d+(?:\.\d+)?)\s*GB', vram_text, re.IGNORECASE)
        if v_match:
            result["gpu_vram_gb"] = float(v_match.group(1))
            result["is_dedicated"] = True
    elif result["is_dedicated"]:
        # Fallback search from GPU name
        v_in_name = re.search(r'(\d+)\s*gb', c_lower)
        if v_in_name:
            result["gpu_vram_gb"] = float(v_in_name.group(1))
        else:
            # Standard known VRAM capacities for dedicated laptop GPUs
            if re.search(r'rtx\s*4090|5090', c_lower):
                result["gpu_vram_gb"] = 16.0
            elif re.search(r'rtx\s*4080|5080', c_lower):
                result["gpu_vram_gb"] = 12.0
            elif re.search(r'rtx\s*(?:4070|4060|5060|5070|3080|3070)', c_lower):
                result["gpu_vram_gb"] = 8.0
            elif re.search(r'rtx\s*(?:4050|3060|2060)', c_lower):
                result["gpu_vram_gb"] = 6.0
            elif re.search(r'rtx\s*(?:3050|2050)|gtx\s*1650|rx\s*6500|arc\s*a370m', c_lower):
                result["gpu_vram_gb"] = 4.0
            elif re.search(r'rx\s*6600|arc\s*(?:a550m|a730m)', c_lower):
                result["gpu_vram_gb"] = 8.0
            elif re.search(r'arc\s*a770m', c_lower):
                result["gpu_vram_gb"] = 16.0
            else:
                result["gpu_vram_gb"] = 4.0

    # GPU Tier (0: basic iGPU, 1: powerful iGPU, 2: entry dGPU, 3: mid dGPU, 4: high dGPU, 5: flagship dGPU)
    if re.search(r'rtx\s*(?:4080|4090|5080|5090)|m4\s*max|m3\s*max', c_lower):
        result["gpu_tier"] = 5
    elif re.search(r'rtx\s*(?:4070|4060|5060|5070|3080|3070)|m4\s*pro|m3\s*pro|m2\s*max', c_lower):
        result["gpu_tier"] = 4
    elif re.search(r'rtx\s*(?:4050|3060|2060)|rx\s*(?:7600|6600)|arc\s*(?:a730m|a770m)', c_lower):
        result["gpu_tier"] = 3
    elif re.search(r'rtx\s*(?:3050|2050)|gtx\s*1650|rx\s*6500|arc\s*a370m', c_lower):
        result["gpu_tier"] = 2
    elif re.search(r'iris\s*xe|radeon\s*780m|radeon\s*680m|radeon\s*890m|intel\s*arc\b|apple\s*\d+\s*core|apple\s*m\d', c_lower):
        result["gpu_tier"] = 1
    else:
        result["gpu_tier"] = 0

    return result

def normalize_battery(battery_text: Optional[str], adapter_text: Optional[str] = None) -> Dict[str, Any]:
    result = {"battery_wh": None, "charger_w": None}
    combined = f"{battery_text or ''} {adapter_text or ''}"
    
    # Battery Wh
    wh_match = re.search(r'(\d+(?:\.\d+)?)\s*wh\b', combined, re.IGNORECASE)
    if wh_match:
        result["battery_wh"] = float(wh_match.group(1))
        
    # Charger W
    w_match = re.search(r'(\d{2,3})\s*W\b', combined)
    if w_match:
        result["charger_w"] = int(w_match.group(1))
        
    return result

def normalize_os(text: Optional[str]) -> str:
    if not text:
        return "Windows"
    t = text.lower()
    if "mac" in t or "apple" in t:
        return "macOS"
    if "chrome" in t:
        return "ChromeOS"
    if "linux" in t or "ubuntu" in t:
        return "Linux"
    if "dos" in t:
        return "DOS"
    return "Windows"
