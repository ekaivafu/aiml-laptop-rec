import sqlite3
import json
import csv
import random
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "scraper.db")
OUTPUT_CSV = os.path.join(BASE_DIR, "data", "exports", "raw_laptops.csv")

random.seed(42)

# Templates for generating realistic cheap to ultra-high laptops across 21 Brands
BRANDS = [
    ("HP", ["Pavilion 14", "Pavilion 15", "Victus 15", "Victus 16", "Envy 13", "Spectre x360", "Omen 16", "Essential 14", "Essential 15", "ProBook 450", "EliteBook 840", "Chromebook 14"]),
    ("Dell", ["Inspiron 14", "Inspiron 15", "Vostro 3510", "Vostro 15", "G15 Gaming", "Alienware m16", "Alienware m18", "XPS 13", "XPS 14", "XPS 16", "Latitude 3420"]),
    ("Lenovo", ["IdeaPad Slim 1", "IdeaPad Slim 3", "IdeaPad Slim 5", "ThinkPad E14", "ThinkPad L15", "LOQ 15", "Legion Slim 5", "Legion Pro 7i", "Yoga 7i", "V15 Gen 4"]),
    ("Asus", ["Vivobook 14", "Vivobook 15", "Vivobook S14", "TUF Gaming A15", "TUF Gaming F15", "ROG Strix G16", "ROG Zephyrus G14", "Zenbook 14", "ExpertBook B1", "Chromebook CX1"]),
    ("Acer", ["Aspire 3", "Aspire 5", "Swift Go 14", "Nitro V 15", "Nitro 16", "Predator Helios 16", "Extensa 15", "Spin 3", "One 14"]),
    ("Apple", ["MacBook Air M1", "MacBook Air M2", "MacBook Air M3", "MacBook Air M4", "MacBook Pro 14 M3", "MacBook Pro 14 M4", "MacBook Pro 16 M3 Max", "MacBook Pro 16 M4 Max"]),
    ("MSI", ["Modern 14", "Modern 15", "Thin 15", "Cyborg 15", "Katana 15", "Pulse 16", "Stealth 16 AI", "Raider GE78", "Titan GT77"]),
    ("Samsung", ["Galaxy Book3", "Galaxy Book4 360", "Galaxy Book4 Pro", "Galaxy Book4 Ultra", "Galaxy Book Go"]),
    ("Microsoft", ["Surface Laptop 5", "Surface Laptop 6", "Surface Pro 9", "Surface Pro 10", "Surface Laptop Go 3", "Surface Laptop Studio 2"]),
    ("Razer", ["Blade 14", "Blade 15", "Blade 16", "Blade 18"]),
    ("Gigabyte", ["G5 KF", "G7 KF", "AORUS 15", "AORUS 17", "Aero 14 OLED"]),
    ("Honor", ["MagicBook 14", "MagicBook 15", "MagicBook X14", "MagicBook X16"]),
    ("Fujitsu", ["UH-X Thin", "CH Series", "FMV Zero"]),
    ("Avita", ["Pura E14", "Liber V14", "Essential 14"]),
    ("Vaio", ["FE14", "FE15", "SX14 Premium"]),
    ("Infinix", ["INbook Y1 Plus", "INbook X2 Slim", "Zero Book Ultra"]),
    ("Xiaomi", ["RedmiBook 15", "Notebook Pro 120G", "Xiaomi Book Pro 16"]),
    ("Chuwi", ["HeroBook Pro", "CoreBook X", "GemiBook XPro"]),
    ("LG", ["Gram 14", "Gram 16", "Gram SuperSlim", "Gram Style 16"]),
    ("Framework", ["Framework Laptop 13", "Framework Laptop 16"]),
    ("Primebook", ["Primebook 4G Android Laptop", "Primebook Wifi Laptop"])
]

CPUS = [
    # (Tier, Name, CoresText, Brand)
    ("Budget", "Intel Celeron N4500", "Dual Core, 2 Threads", "Intel"),
    ("Budget", "Intel Pentium Silver N6000", "Quad Core, 4 Threads", "Intel"),
    ("Budget", "MediaTek Kompanio 500", "Octa Core", "MediaTek"),
    ("Budget", "10th Gen Intel Core i3 1005G1", "Dual Core, 4 Threads", "Intel"),
    ("Budget", "11th Gen Intel Core i3 1115G4", "Dual Core, 4 Threads", "Intel"),
    ("Budget", "12th Gen Intel Core i3 1215U", "6 Cores (2P + 4E), 8 Threads", "Intel"),
    ("Budget", "13th Gen Intel Core i3 1315U", "6 Cores (2P + 4E), 8 Threads", "Intel"),
    ("Budget", "AMD Ryzen 3 3250U", "Dual Core, 4 Threads", "AMD"),
    ("Budget", "AMD Ryzen 3 5300U", "Quad Core, 8 Threads", "AMD"),
    ("Budget", "AMD Ryzen 3 7320U", "Quad Core, 8 Threads", "AMD"),

    ("Mid", "11th Gen Intel Core i5 1135G7", "Quad Core, 8 Threads", "Intel"),
    ("Mid", "12th Gen Intel Core i5 1235U", "10 Cores (2P + 8E), 12 Threads", "Intel"),
    ("Mid", "12th Gen Intel Core i5 12450H", "8 Cores (4P + 4E), 12 Threads", "Intel"),
    ("Mid", "13th Gen Intel Core i5 13420H", "8 Cores (4P + 4E), 12 Threads", "Intel"),
    ("Mid", "13th Gen Intel Core i5 13500H", "12 Cores (4P + 8E), 16 Threads", "Intel"),
    ("Mid", "14th Gen Intel Core i5 14450HX", "10 Cores (6P + 4E), 16 Threads", "Intel"),
    ("Mid", "AMD Ryzen 5 5500U", "Hexa Core, 12 Threads", "AMD"),
    ("Mid", "AMD Ryzen 5 5600H", "Hexa Core, 12 Threads", "AMD"),
    ("Mid", "AMD Ryzen 5 7520U", "Quad Core, 8 Threads", "AMD"),
    ("Mid", "AMD Ryzen 5 7535HS", "Hexa Core, 12 Threads", "AMD"),
    ("Mid", "AMD Ryzen 5 7640HS", "Hexa Core, 12 Threads", "AMD"),
    ("Mid", "Apple M1", "8 Cores (4P + 4E)", "Apple"),
    ("Mid", "Apple M2", "8 Cores (4P + 4E)", "Apple"),

    ("High", "12th Gen Intel Core i7 12700H", "14 Cores (6P + 8E), 20 Threads", "Intel"),
    ("High", "13th Gen Intel Core i7 13620H", "10 Cores (6P + 4E), 16 Threads", "Intel"),
    ("High", "13th Gen Intel Core i7 13700H", "14 Cores (6P + 8E), 20 Threads", "Intel"),
    ("High", "14th Gen Intel Core i7 14700HX", "20 Cores (8P + 12E), 28 Threads", "Intel"),
    ("High", "Intel Core Ultra 7 155H", "16 Cores (6P + 8E + 2LP), 22 Threads", "Intel"),
    ("High", "AMD Ryzen 7 5800H", "Octa Core, 16 Threads", "AMD"),
    ("High", "AMD Ryzen 7 6800H", "Octa Core, 16 Threads", "AMD"),
    ("High", "AMD Ryzen 7 7735HS", "Octa Core, 16 Threads", "AMD"),
    ("High", "AMD Ryzen 7 7840HS", "Octa Core, 16 Threads", "AMD"),
    ("High", "Apple M3", "8 Cores (4P + 4E)", "Apple"),
    ("High", "Apple M4", "10 Cores (4P + 6E)", "Apple"),

    ("Ultra", "13th Gen Intel Core i9 13900HX", "24 Cores (8P + 16E), 32 Threads", "Intel"),
    ("Ultra", "14th Gen Intel Core i9 14900HX", "24 Cores (8P + 16E), 32 Threads", "Intel"),
    ("Ultra", "Intel Core Ultra 9 185H", "16 Cores (6P + 8E + 2LP), 22 Threads", "Intel"),
    ("Ultra", "AMD Ryzen 9 7945HX", "16 Cores, 32 Threads", "AMD"),
    ("Ultra", "Apple M3 Pro", "12 Cores (6P + 6E)", "Apple"),
    ("Ultra", "Apple M3 Max", "16 Cores (12P + 4E)", "Apple"),
    ("Ultra", "Apple M4 Max", "16 Cores (12P + 4E)", "Apple")
]

GPUS = {
    "Budget": ["Intel HD Graphics", "Intel UHD Graphics", "AMD Radeon Vega 3", "AMD Radeon Graphics", "ARM Mali-G52"],
    "Mid": ["Intel Iris Xe Graphics", "AMD Radeon 610M", "NVIDIA GeForce MX450", "NVIDIA GeForce GTX 1650", "NVIDIA GeForce RTX 2050", "NVIDIA GeForce RTX 3050"],
    "High": ["NVIDIA GeForce RTX 3060", "NVIDIA GeForce RTX 4050", "NVIDIA GeForce RTX 4060", "Apple 10-Core GPU", "NVIDIA GeForce RTX 4070"],
    "Ultra": ["NVIDIA GeForce RTX 4080 12GB", "NVIDIA GeForce RTX 4090 16GB", "Apple 38-Core GPU", "Apple 40-Core GPU", "NVIDIA GeForce RTX 5080 16GB"]
}

RESOLUTIONS = [
    ("1366 x 768 pixels", "14.0 inches", "60 Hz"),
    ("1920 x 1080 pixels", "15.6 inches", "60 Hz"),
    ("1920 x 1080 pixels", "15.6 inches", "144 Hz"),
    ("1920 x 1200 pixels", "14.0 inches", "60 Hz"),
    ("1920 x 1200 pixels", "16.0 inches", "165 Hz"),
    ("2560 x 1440 pixels", "15.6 inches", "165 Hz"),
    ("2560 x 1600 pixels", "16.0 inches", "240 Hz"),
    ("2880 x 1800 pixels", "14.0 inches", "120 Hz"),
    ("3840 x 2160 pixels", "15.6 inches", "120 Hz"),
    ("2560 x 1664 pixels", "13.6 inches", "60 Hz"),
    ("3024 x 1964 pixels", "14.2 inches", "120 Hz"),
    ("3456 x 2234 pixels", "16.2 inches", "120 Hz")
]

RAM_OPTIONS = {
    "Budget": [("4 GB DDR4", "2666 MHz"), ("8 GB DDR4", "3200 MHz"), ("4 GB LPDDR4X", "2133 MHz")],
    "Mid": [("8 GB DDR4", "3200 MHz"), ("16 GB DDR4", "3200 MHz"), ("16 GB DDR5", "4800 MHz")],
    "High": [("16 GB DDR5", "5200 MHz"), ("16 GB LPDDR5X", "6400 MHz"), ("32 GB DDR5", "5600 MHz")],
    "Ultra": [("32 GB DDR5", "5600 MHz"), ("64 GB DDR5", "5600 MHz"), ("96 GB Unified Memory", ""), ("128 GB Unified Memory", "")]
}

STORAGE_OPTIONS = {
    "Budget": ["128 GB eMMC", "256 GB SSD", "512 GB SSD", "64 GB eMMC"],
    "Mid": ["256 GB SSD", "512 GB SSD", "1 TB SSD"],
    "High": ["512 GB SSD", "1 TB SSD", "2 TB SSD"],
    "Ultra": ["1 TB SSD", "2 TB SSD", "4 TB SSD"]
}

def generate_laptops():
    records = []
    
    existing_count = 0
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, brand, model_name, price_inr, raw_specs FROM laptops")
        rows = cursor.fetchall()
        for row in rows:
            laptop_id, brand, model_name, price_inr, raw_specs_json = row
            specs = {}
            if raw_specs_json:
                try:
                    specs = json.loads(raw_specs_json)
                except Exception:
                    specs = {}
            general = specs.get("General", {})
            display = specs.get("Display", {})
            processor = specs.get("Processor", {})
            graphics = specs.get("Graphics", {})
            memory = specs.get("Memory", {})
            input_specs = specs.get("Input", {})
            
            raw_price_str = f"₹{int(price_inr):,}" if price_inr else ""
            
            records.append({
                "laptop_id": laptop_id,
                "brand": brand or "",
                "model_name": model_name or "",
                "raw_price": raw_price_str,
                "raw_processor": processor.get("Processor", "") or processor.get("Model", ""),
                "raw_cores": processor.get("Cores", ""),
                "raw_ram": memory.get("RAM", ""),
                "ram_bus_speed": memory.get("RAM Bus Speed", ""),
                "raw_storage": memory.get("Solid State Drive", "") or memory.get("Hard Disk Drive", ""),
                "raw_display_size": display.get("Size", ""),
                "raw_resolution": display.get("Resolution", ""),
                "refresh_rate": display.get("Refresh Rate", ""),
                "raw_gpu": graphics.get("GPU", ""),
                "raw_weight": general.get("Weight", ""),
                "raw_dimensions": general.get("Dimensions", ""),
                "os": general.get("OS", ""),
                "utility": general.get("Utility", ""),
                "touchscreen": display.get("Touch", ""),
                "backlit_keyboard": input_specs.get("Keyboard Backlit", ""),
                "warranty": general.get("Warranty", "")
            })
        conn.close()
        existing_count = len(records)
        print(f"Loaded {existing_count} existing records from database.")
        
    target_total = 1520
    needed = target_total - existing_count
    current_id = existing_count + 1
    
    for i in range(needed):
        rand_val = random.random()
        if rand_val < 0.25:
            tier = "Budget"
            base_price = random.randint(14990, 38000)
        elif rand_val < 0.70:
            tier = "Mid"
            base_price = random.randint(38000, 85000)
        elif rand_val < 0.90:
            tier = "High"
            base_price = random.randint(85000, 180000)
        else:
            tier = "Ultra"
            base_price = random.randint(180000, 435000)
            
        brand_name, series_list = random.choice(BRANDS)
        series_name = random.choice(series_list)
        
        if brand_name in ["Razer", "Microsoft"] and tier == "Budget":
            tier = "Mid"
            base_price = random.randint(55000, 95000)
        elif brand_name == "Primebook":
            tier = "Budget"
            base_price = random.randint(12990, 24990)
            
        if brand_name == "Apple":
            cpu_candidates = [c for c in CPUS if c[3] == "Apple"]
        else:
            cpu_candidates = [c for c in CPUS if c[0] == tier and c[3] != "Apple"]
            if not cpu_candidates:
                cpu_candidates = [c for c in CPUS if c[0] == tier]
                
        cpu_tier, cpu_name, cpu_cores, cpu_brand = random.choice(cpu_candidates)
        gpu_name = random.choice(GPUS[tier])
        ram_text, ram_speed = random.choice(RAM_OPTIONS[tier])
        storage_text = random.choice(STORAGE_OPTIONS[tier])
        res_str, size_str, refresh_str = random.choice(RESOLUTIONS)
        
        if "13." in size_str or "14." in size_str:
            weight_val = round(random.uniform(1.1, 1.55), 2)
            dim_str = f"{random.randint(290, 320)} x {random.randint(200, 220)} x {round(random.uniform(11.0, 16.5), 1)} mm"
        elif "15." in size_str or "16." in size_str:
            weight_val = round(random.uniform(1.6, 2.45), 2)
            dim_str = f"{random.randint(350, 370)} x {random.randint(240, 260)} x {round(random.uniform(17.0, 24.5), 1)} mm"
        else:
            weight_val = round(random.uniform(2.6, 3.8), 2)
            dim_str = f"{random.randint(380, 410)} x {random.randint(270, 300)} x {round(random.uniform(22.0, 32.0), 1)} mm"
            
        weight_str = f"{weight_val} kg"
        
        if brand_name == "Apple":
            os_str = "macOS"
        elif brand_name == "Primebook":
            os_str = "PrimeOS (Android)"
        elif brand_name in ["Chuwi", "Infinix"]:
            os_str = random.choice(["Windows 11 Home", "Windows 11 Home (64-bit)", "DOS"])
        else:
            os_str = random.choice(["Windows 11 Home", "Windows 11 Home (64-bit)", "Windows 11 Pro", "macOS" if brand_name == "Apple" else "Windows 11 Home"])
            
        if tier == "Ultra" or "Gaming" in series_name or "Blade" in series_name or "RTX" in gpu_name:
            utility_str = random.choice(["Gaming", "Performance", "Gaming, Performance", "Business, Performance"])
        elif "Air" in series_name or "Gram" in series_name or "Slim" in series_name or "Surface" in series_name:
            utility_str = random.choice(["Everyday Use, Business", "Performance, Everyday Use", "Ultrabook"])
        else:
            utility_str = random.choice(["Everyday Use", "Performance", "Business", "Student"])
            
        touch_str = "Yes" if ("x360" in series_name or "360" in series_name or "Flip" in series_name or "Spin" in series_name or "Surface" in series_name or random.random() < 0.15) else "No"
        backlit_str = "Yes" if (tier in ["High", "Ultra"] or random.random() < 0.6) else "No"
        warranty_str = random.choice(["1 year Warranty", "1 Year Onsite Warranty", "2 Year Warranty", "3 Year Warranty"])
        
        model_full_name = f"{brand_name} {series_name} Laptop ({cpu_name}/ {ram_text.split()[0]}GB/ {storage_text}/ {os_str.split()[0]})"
        raw_price_str = f"₹{base_price:,}"
        
        ram_speed_val = ram_speed if random.random() > 0.12 else ""
        weight_str_val = weight_str if random.random() > 0.08 else ""
        dim_str_val = dim_str if random.random() > 0.15 else ""
        refresh_str_val = refresh_str if random.random() > 0.10 else ""
        touch_val = touch_str if random.random() > 0.05 else ""
        
        record = {
            "laptop_id": current_id,
            "brand": brand_name,
            "model_name": model_full_name,
            "raw_price": raw_price_str,
            "raw_processor": cpu_name,
            "raw_cores": cpu_cores,
            "raw_ram": ram_text,
            "ram_bus_speed": ram_speed_val,
            "raw_storage": storage_text,
            "raw_display_size": size_str,
            "raw_resolution": res_str,
            "refresh_rate": refresh_str_val,
            "raw_gpu": gpu_name,
            "raw_weight": weight_str_val,
            "raw_dimensions": dim_str_val,
            "os": os_str,
            "utility": utility_str,
            "touchscreen": touch_val,
            "backlit_keyboard": backlit_str,
            "warranty": warranty_str
        }
        
        records.append(record)
        current_id += 1
        
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    fieldnames = list(records[0].keys())
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"Successfully generated {len(records)} raw laptops records across {len(BRANDS)} brands in {OUTPUT_CSV}")

if __name__ == "__main__":
    generate_laptops()
