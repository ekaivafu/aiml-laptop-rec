import re
from typing import Tuple, Optional, Any

def is_laptop_2022_or_newer(
    model_name: Optional[str] = "",
    cpu_model: Optional[str] = "",
    cpu_brand: Optional[str] = "",
    cpu_family: Optional[str] = "",
    cpu_generation: Optional[Any] = None,
    raw_specs: Optional[Any] = None
) -> Tuple[bool, str]:
    """
    Evaluates whether a laptop was launched in 2022 or newer.
    
    Criteria:
    - Rejects models with explicit launch years <= 2021 in title.
    - Intel: Requires 12th Gen+, Core Ultra (Series 1 & 2), Core 3/5/7 (Series 1 & 2), 
      or Alder Lake-N (N100, N95). Rejects 1st-11th Gen, Celeron N4020/N4500, Pentium Gold.
    - AMD: Retains Ryzen 5000, 6000, 7000, 8000, AI 300, and Athlon 7000 series.
      Rejects Ryzen 3000/4000 series and Athlon 3000 series.
    - Apple: Retains Apple Silicon M2, M3, M4, and A18 Pro. Rejects M1 (2020 launch).
    - Qualcomm: Retains Snapdragon X Elite, X Plus, 8cx Gen 3. Rejects 7c / 8cx Gen 1/2.
    """
    name = (model_name or "").lower()
    model = (cpu_model or "").lower()
    brand = (cpu_brand or "").lower()
    gen = None
    if cpu_generation is not None:
        try:
            gen = int(float(str(cpu_generation)))
        except (ValueError, TypeError):
            gen = None

    # 1. Explicit pre-2022 year in title (e.g. 2020, 2021, 2019)
    m_old_year = re.search(r'\b(201\d|2020|2021)\b', name)
    if m_old_year:
        return False, f"Explicit pre-2022 year in title: {m_old_year.group(1)}"

    # 2. Modern Intel checks (Ultra, Core 3/5/7 1xx/2xx, N-series)
    if "ultra" in name or "ultra" in model:
        return True, "Intel Core Ultra (2023+)"
    if re.search(r'\bcore\s*(?:3|5|7)\s+(?:1\d{2}[a-z]|2\d{2}[a-z])', name) or re.search(r'\b(1\d{2}[a-z]|2\d{2}[a-z])\b', model):
        if "intel" in brand or "intel" in name:
            return True, "Intel Core Series 1/2 (2024+)"
    if re.search(r'\b(n100|n200|n300|n95|n97)\b', model):
        return True, "Intel Alder Lake-N (2023+)"

    # 3. AMD processors
    if brand == "amd" or "ryzen" in model or "ryzen" in name or "athlon" in model:
        # Pre-2022 AMD
        if any(x in model for x in ["3200u", "3500u", "3700u", "4500u", "4700u", "4800h", "4600h", "3050u"]):
            return False, f"AMD Ryzen 3000/4000 series ({model})"
        # 6000 / 7000 / 8000 / AI series
        if re.search(r'\b(7\d{3}|8\d{3}|6\d{3})\b', model) or (gen in [6, 7, 8]):
            return True, f"AMD Ryzen 6000/7000/8000 series (2022+)"
        if "ai 9" in model or "ai 300" in model or "strix" in model:
            return True, "AMD Ryzen AI series (2024+)"
        # 5000 series (widely produced & launched through 2022/2023)
        if re.search(r'\b5\d{3}\b', model) or gen == 5:
            return True, "AMD Ryzen 5000 series (2021-2022)"
        return True, "AMD processor (2022+)"

    # 4. Intel processors
    if brand == "intel" or "intel" in name or (gen is not None and gen >= 10):
        # Explicit pre-2022 Intel CPUs
        if any(x in model for x in [
            "1135g7", "1115g4", "11800h", "11400h", "1165g7", "11300h",
            "1005g1", "10210u", "10750h", "10300h", "10110u", "1065g7",
            "n4020", "n4000", "n4500", "n5030", "6405u", "7505"
        ]):
            return False, f"Pre-2022 Intel CPU ({model})"
        # Legacy Gen <= 11
        if gen is not None and 1 <= gen <= 11 and "ultra" not in name:
            if not re.search(r'\b(1\d{2}[a-z]|2\d{2}[a-z])\b', model):
                return False, f"Intel legacy Gen <= 11 ({gen}th Gen)"
        if gen in [12, 13, 14]:
            return True, f"Intel {gen}th Gen (2022+)"
        if re.search(r'\b(12\d{3}|13\d{3}|14\d{3})[a-z]*\b', model):
            return True, "Intel 12th/13th/14th Gen model (2022+)"

    # 5. Apple Silicon
    if brand == "apple" or "apple" in name or any(x in model for x in ["m1", "m2", "m3", "m4"]):
        if "m1" in model or "m1" in name:
            return False, "Apple M1 (late 2020 launch)"
        if any(x in model or x in name for x in ["m2", "m3", "m4", "a18 pro"]):
            return True, "Apple M2/M3/M4/A18 (2022+)"

    # 6. Qualcomm Snapdragon
    if "snapdragon" in model or "snapdragon" in name:
        if any(x in model or x in name for x in ["x elite", "x plus", "8cx gen 3"]):
            return True, "Snapdragon X Elite/Plus or 8cx Gen 3 (2022+)"
        return False, "Older Snapdragon generation"

    # Default to True unless older markers are present
    return True, "Default 2022+ (no older markers)"
