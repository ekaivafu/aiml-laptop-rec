from typing import Dict, Any, List

def validate_laptop_data(data: Dict[str, Any]) -> List[str]:
    """
    Validates the normalized data and returns a list of warning messages.
    Does not delete the data, just flags potential parsing or spec issues.
    """
    warnings = []
    
    # Check Price
    price = data.get("price_inr")
    if price is not None:
        if price < 10000:
            warnings.append(f"Suspiciously low price: {price}")
        elif price > 1000000:
            warnings.append(f"Suspiciously high price: {price}")
    
    # Check RAM
    ram = data.get("ram_gb")
    if ram is not None:
        if ram not in [4, 8, 12, 16, 18, 24, 32, 48, 64, 96, 128]:
            warnings.append(f"Unusual RAM capacity: {ram}GB")
            
    # Check Storage
    storage = data.get("storage_gb")
    if storage is not None:
        if storage < 32 or storage > 8192:
            warnings.append(f"Unusual Storage capacity: {storage}GB")
            
    # Check Display
    screen = data.get("screen_size_in")
    if screen is not None:
        if screen < 10.0 or screen > 21.0:
            warnings.append(f"Unusual screen size: {screen} inches")
            
    # Check Refresh Rate
    refresh = data.get("refresh_rate_hz")
    if refresh is not None:
        if refresh < 40 or refresh > 360:
            warnings.append(f"Unusual display refresh rate: {refresh} Hz")

    # Check Brightness
    nits = data.get("brightness_nits")
    if nits is not None:
        if nits < 150 or nits > 2000:
            warnings.append(f"Unusual brightness value: {nits} nits")

    # Check CPU Cores
    cores = data.get("cpu_cores")
    if cores is not None:
        if cores < 2 or cores > 32:
            warnings.append(f"Unusual CPU cores count: {cores}")

    # Check GPU VRAM
    vram = data.get("gpu_vram_gb")
    if vram is not None and vram > 0:
        if vram not in [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0]:
            warnings.append(f"Unusual GPU VRAM capacity: {vram} GB")

    # Check Weight
    weight = data.get("weight_kg")
    if weight is not None:
        if weight < 0.5 or weight > 6.0:
            warnings.append(f"Unusual weight: {weight} kg")
            
    # Check Battery
    battery = data.get("battery_wh")
    if battery is not None:
        if battery < 20 or battery > 105:
            warnings.append(f"Unusual battery capacity: {battery} Wh")

    return warnings
