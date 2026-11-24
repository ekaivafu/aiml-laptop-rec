import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import os

BASE_URL = "https://www.smartprix.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def discover_smartprix_laptops(limit=10):
    """Step 1: Discover laptop URLs from Smartprix catalog listing page."""
    print(f"🔍 [Smartprix Scraper] Discovering laptop product URLs (Limit: {limit})...")
    catalog_url = f"{BASE_URL}/laptops"
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    laptop_urls = []
    try:
        response = session.get(catalog_url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # Smartprix product URLs contain '-ppd' in href
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/laptops/" in href and "-ppd" in href:
                    full_url = BASE_URL + href if href.startswith("/") else href
                    if full_url not in laptop_urls:
                        laptop_urls.append(full_url)
                        if len(laptop_urls) >= limit:
                            break
        else:
            print(f"⚠️ Failed to load catalog: Status code {response.status_code}")
    except Exception as e:
        print(f"❌ Error fetching Smartprix catalog: {e}")
        
    print(f"✅ Discovered {len(laptop_urls)} laptop URLs.")
    return laptop_urls

def scrape_smartprix_laptop_details(product_url):
    """Step 2: Scrape raw specifications and price from an individual Smartprix laptop page."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    print(f"🌐 Scraping: {product_url}")
    try:
        response = session.get(product_url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Status {response.status_code} for {product_url}")
            return None
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Title
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Unknown Laptop"
        
        # 2. Price
        price_el = soup.find("span", class_=lambda c: c and "price" in c.lower())
        price_text = price_el.get_text(strip=True) if price_el else ""
        
        # 3. Specs Table
        raw_specs = {}
        spec_tables = soup.find_all("table")
        for table in spec_tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    val = cols[1].get_text(strip=True)
                    if key and val:
                        raw_specs[key] = val
                        
        scraped_data = {
            "url": product_url,
            "title": title,
            "raw_price": price_text,
            "raw_specs_count": len(raw_specs),
            "raw_specs_json": json.dumps(raw_specs)
        }
        return scraped_data
        
    except Exception as e:
        print(f"❌ Error scraping {product_url}: {e}")
        return None

def main():
    print("=" * 60)
    print("🚀 SMARTPRIX LAPTOP WEB SCRAPER DEMO")
    print("=" * 60)
    
    urls = discover_smartprix_laptops(limit=10)
    
    scraped_results = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Scraping product page...")
        data = scrape_smartprix_laptop_details(url)
        if data:
            scraped_results.append(data)
        time.sleep(0.5) # respectful rate limiting delay
        
    if scraped_results:
        df = pd.DataFrame(scraped_results)
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "exports", "smartprix_scraped_demo.csv")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print("\n" + "=" * 60)
        print(f"✅ Scraping completed! {len(scraped_results)} raw laptops exported to:")
        print(f"📁 {output_path}")
        print("=" * 60)
    else:
        print("❌ No data scraped.")

if __name__ == "__main__":
    main()
