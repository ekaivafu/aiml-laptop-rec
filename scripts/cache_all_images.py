import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

CACHE_DIR = "data/cache/images"
os.makedirs(CACHE_DIR, exist_ok=True)

df = pd.read_csv("data/exports/laptops.csv")
valid = df[df["image_url"].notna() & df["image_url"].str.startswith("http")]
print(f"Total laptops with image_url to cache: {len(valid)}")

def cache_one(row):
    lid = row["id"]
    url = row["image_url"]
    dest = os.path.join(CACHE_DIR, f"{lid}.webp")
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        return True
    
    # Request optimized dimensions -w400-h400 for 75% smaller footprint and fast transfer
    opt_url = url.replace("-w1200-h1200", "-w400-h400")
    req = urllib.request.Request(opt_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = resp.read()
            if len(data) > 500:
                with open(dest, "wb") as f:
                    f.write(data)
                return True
    except Exception:
        # Fallback to original URL if -w400-h400 fails
        try:
            req_orig = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_orig, timeout=4) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(dest, "wb") as f:
                        f.write(data)
                    return True
        except Exception:
            return False
    return False

t0 = time.time()
with ThreadPoolExecutor(max_workers=30) as executor:
    results = list(executor.map(cache_one, [row for _, row in valid.iterrows()]))

elapsed = time.time() - t0
cached_count = sum(results)
print(f"Successfully cached {cached_count}/{len(valid)} images in {elapsed:.2f}s ({cached_count/elapsed:.1f} img/s)!")
