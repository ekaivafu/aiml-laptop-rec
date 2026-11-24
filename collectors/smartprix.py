from typing import List, Dict, Any, Tuple, Optional
from bs4 import BeautifulSoup
import time
import json
import re
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from .base import BaseCollector

class SmartprixCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.smartprix.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Upgrade-Insecure-Requests": "1"
        })
        
    @classmethod
    def get_discovery_seeds(cls) -> List[str]:
        """Generate an exhaustive matrix of brand, processor, utility, and price category URLs."""
        seeds = [
            "/laptops",
            # General Lists & Utility
            "/laptops/utility-gaming", "/laptops/with-touch_screen", "/laptops/windows_11-os",
            "/laptops/16_gb_above-ram", "/laptops/intel-core-ultra-laptops-list",
            "/laptops/apple-m4-chip-macbooks-list", "/laptops/apple-brand",
            "/laptops/rtx_4050-gpu", "/laptops/rtx_4060-gpu", "/laptops/rtx_3050-gpu",
            "/laptops/rtx_4070-gpu", "/laptops/rtx_4080-gpu", "/laptops/rtx_2050-gpu",
            "/laptops/best-gaming-laptops-under-200000-list",
            "/laptops/best-laptops-under-40000-list", "/laptops/best-laptops-under-50000-list",
            "/laptops/best-laptops-under-60000-list", "/laptops/best-laptops-under-70000-list",
            "/laptops/best-laptops-under-80000-list", "/laptops/best-laptops-under-100000-list",
            "/laptops/best-laptops-under-150000-list", "/laptops/cheap-laptops-list"
        ]
        
        # Primary Brands
        brands = [
            "lenovo-brand", "asus-brand", "hp-brand", "dell-brand", "acer-brand",
            "apple-brand", "msi-brand", "samsung-brand", "infinix-brand", "xiaomi-brand",
            "honor-brand", "lg-brand", "realme-brand", "gigabyte-brand", "alienware-brand",
            "zebronics-brand", "chuwi-brand", "microsoft-brand"
        ]
        for b in brands:
            seeds.append(f"/laptops/{b}")
            
        # Brand + Sub-filter combinations
        filters = [
            "intel_core_i5-cpu", "intel_core_i7-cpu", "intel_core_i3-cpu", "intel_core_i9-cpu",
            "amd_ryzen_5-cpu", "amd_ryzen_7-cpu", "amd_ryzen_9-cpu", "utility-gaming",
            "16_gb_above-ram", "price-below_40000", "price-40000_to_60000",
            "price-60000_to_80000", "price-80000_to_100000", "price-100000_to_150000",
            "price-above_150000"
        ]
        for b in ["lenovo-brand", "asus-brand", "hp-brand", "dell-brand", "acer-brand", "msi-brand"]:
            for f in filters:
                seeds.append(f"/laptops/{b}/{f}")
                
        return seeds

    DISCOVERY_SEEDS = []

    def discover_urls(self, limit: int = 100, start_page: int = 1) -> List[str]:
        """
        Quickly discover laptop product URLs across categories, brands, price segments,
        and processor tiers using fast HTTP requests.
        """
        urls = []
        seed_list = self.get_discovery_seeds()
        if start_page > 1:
            seed_list = seed_list[max(0, start_page - 1):]
        
        for path in seed_list:
            if len(urls) >= limit:
                break
            search_url = f"{self.base_url}{path}"
            try:
                resp = self.session.get(search_url, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    hrefs = [a.get('href') for a in soup.find_all('a', href=True) if '-ppd' in a.get('href', '') and '/laptops/' in a.get('href', '')]
                    for href in hrefs:
                        full_url = self.base_url + href if href.startswith('/') else href
                        if full_url not in urls and '-ppd' in full_url:
                            urls.append(full_url)
                            if len(urls) >= limit:
                                break
                    time.sleep(0.1)
                elif resp.status_code in [403, 429]:
                    print(f"HTTP {resp.status_code} on {path}, slowing down...")
                    time.sleep(1.0)
            except Exception:
                continue

        # If seeds yielded fewer than limit, expand BFS over discovered product pages
        idx = 0
        while idx < len(urls) and len(urls) < limit:
            sample_url = urls[idx]
            idx += 1
            try:
                resp = self.session.get(sample_url, timeout=8)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    related = [
                        a.get('href') for a in soup.find_all('a', href=True)
                        if '-ppd' in a.get('href', '') and '/laptops/' in a.get('href', '')
                    ]
                    for href in related:
                        full_url = self.base_url + href if href.startswith('/') else href
                        if full_url not in urls and '-ppd' in full_url:
                            urls.append(full_url)
                            if len(urls) >= limit:
                                break
                    time.sleep(0.05)
            except Exception:
                continue

        return urls

    def _discover_urls_playwright(self, limit: int = 100, start_page: int = 1) -> List[str]:
        """Fallback Playwright discovery with headless browser."""
        urls = []
        page = start_page
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            while len(urls) < limit:
                page_obj = context.new_page()
                search_url = f"{self.base_url}/laptops?page={page}"
                try:
                    page_obj.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    page_obj.wait_for_selector("a[href*='/laptops/']", timeout=15000)
                    hrefs = page_obj.eval_on_selector_all("a[href*='/laptops/']", "elements => elements.map(e => e.getAttribute('href'))")
                    new_urls = 0
                    for href in hrefs:
                        if href and href != '/laptops':
                            full_url = self.base_url + href if href.startswith('/') else href
                            if full_url not in urls and '-ppd' in full_url:
                                urls.append(full_url)
                                new_urls += 1
                                if len(urls) >= limit:
                                    break
                    if new_urls == 0:
                        page_obj.close()
                        break
                    page += 1
                    page_obj.close()
                    time.sleep(1)
                except Exception as e:
                    print(f"Playwright discovery error on page {page}: {e}")
                    page_obj.close()
                    break
            browser.close()
        return urls

    def fetch_product(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Fast product fetch via HTTP session with retries and backoff.
        Smartprix embeds full specs in static HTML.
        """
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=12)
                if resp.status_code == 200 and len(resp.text) > 5000:
                    return resp.text, None
                elif resp.status_code == 429:
                    time.sleep(2.0 * (attempt + 1))
                elif resp.status_code in [500, 502, 503, 504]:
                    time.sleep(1.0)
            except Exception:
                time.sleep(1.0)

        return None, None

    def _fetch_product_playwright(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fallback product fetch via headless Playwright browser."""
        html = None
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page_obj = context.new_page()
            try:
                page_obj.goto(url, wait_until="domcontentloaded", timeout=15000)
                page_obj.wait_for_timeout(1500)
                try:
                    specs_btn = page_obj.get_by_text("VIEW FULL SPECS")
                    if specs_btn.count() > 0:
                        specs_btn.first.click(timeout=3000)
                        page_obj.wait_for_timeout(1000)
                except Exception:
                    pass
                html = page_obj.content()
            except Exception as e:
                print(f"Error in Playwright fetch for {url}: {e}")
            finally:
                page_obj.close()
                browser.close()
                
        return html, None

    def extract_raw_fields(self, html: Optional[str], json_data: Optional[str]) -> Dict[str, Any]:
        data = {
            "model_name": None, "brand": None, "series": None, "model_number": None,
            "price_inr": None, "mrp_inr": None, "availability": None,
            "device_type_raw": None, "utility_raw": None, "os_raw": None,
            "weight_raw": None, "thickness_raw": None, "warranty_raw": None,
            "display_size_raw": None, "resolution_raw": None, "ppi_raw": None,
            "refresh_rate_raw": None, "panel_type_raw": None,
            "touchscreen_raw": None, "anti_glare_raw": None, "features_raw": None,
            "cpu_processor_raw": None, "cpu_brand_raw": None, "cpu_series_raw": None,
            "cpu_model_raw": None, "cpu_generation_raw": None, "cpu_cores_raw": None,
            "cpu_speed_raw": None, "cpu_cache_raw": None,
            "gpu_model": None, "gpu_brand_raw": None, "gpu_vram_raw": None,
            "ram_raw": None, "ram_speed_raw": None, "ram_slots_raw": None, "ram_max_raw": None,
            "storage_raw": None, "storage_interface_raw": None,
            "wifi_raw": None, "bluetooth_raw": None, "usb_ports_raw": None,
            "webcam_raw": None, "fingerprint_sensor_raw": None,
            "backlit_keyboard_raw": None, "microphone_raw": None,
            "battery_raw": None, "adapter_raw": None,
            "shop_links": {}, "store_details": {},
            "min_store_price": None, "best_store": None,
            "raw_specs": {}
        }
        if not html:
            return data
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Authoritative metadata from Schema.org JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                js_data = json.loads(script.string)
                if isinstance(js_data, dict) and js_data.get('@type') == 'Product':
                    if not data["model_name"]:
                        data["model_name"] = js_data.get('name')
                    brand_info = js_data.get('brand')
                    if isinstance(brand_info, dict):
                        data["brand"] = brand_info.get('name')
                    elif isinstance(brand_info, str):
                        data["brand"] = brand_info
                        
                    offer = js_data.get('offers')
                    if isinstance(offer, dict):
                        data["price_inr"] = offer.get('price')
                        data["availability"] = offer.get('availability')
                    break
            except Exception:
                pass

        # Fallback Title & Brand from H1
        if not data["model_name"]:
            title_tag = soup.find('h1')
            if title_tag:
                data["model_name"] = title_tag.text.strip()
        if not data["brand"] and data["model_name"]:
            data["brand"] = data["model_name"].split()[0]
            
        # Fallback Price from price div
        if not data["price_inr"]:
            price_tag = soup.find(class_=lambda c: c and ('price' in str(c).lower() and 'discount' not in str(c).lower()))
            if price_tag:
                match = re.search(r'[\u20b9Rs\.]*\s*([\d,]+)', price_tag.text)
                if match:
                    data["price_inr"] = match.group(1).replace(',', '')

        mrp_tag = soup.find(class_=lambda c: c and ('mrp' in str(c).lower() or 'original' in str(c).lower() or 'old-price' in str(c).lower()))
        if mrp_tag:
            match = re.search(r'[\u20b9Rs\.]*\s*([\d,]+)', mrp_tag.text)
            if match:
                data["mrp_inr"] = match.group(1).replace(',', '')

        # 2. Clean table-based spec extraction from sm-fullspecs-grp
        seen_sections = set()
        spec_groups = soup.find_all(class_='sm-fullspecs-grp')
        
        for grp in spec_groups:
            hdr_el = grp.find(['h3', 'h4', 'h2', 'h5', 'div'])
            section_name = hdr_el.text.strip() if hdr_el else "General"
            
            # Avoid processing duplicate modal groups
            if section_name in seen_sections:
                continue
            seen_sections.add(section_name)
            
            if section_name not in data["raw_specs"]:
                data["raw_specs"][section_name] = {}
                
            for tr in grp.find_all('tr'):
                cells = tr.find_all(['th', 'td'])
                if len(cells) < 2:
                    continue
                key_raw = cells[0].text.strip()
                val_raw = cells[1].text.strip()
                key = key_raw.lower()
                val = val_raw
                
                # Check for boolean check/cross icon inside cell
                is_no = 'cross' in str(cells[1]).lower() or val.lower() == 'no'
                is_yes = 'check' in str(cells[1]).lower() or 'tick' in str(cells[1]).lower() or val.lower() == 'yes'
                bool_str = 'no' if is_no else ('yes' if is_yes else val)
                
                data["raw_specs"][section_name][key_raw] = val_raw
                
                # Section-by-section direct mapping
                if section_name.lower() == 'general':
                    if key == 'series':
                        data["series"] = val
                    elif key == 'model':
                        data["model_number"] = val
                    elif key == 'utility':
                        data["utility_raw"] = val
                    elif key == 'device type':
                        data["device_type_raw"] = val
                    elif key in ['os', 'operating system']:
                        data["os_raw"] = val
                    elif key in ['dimensions', 'thickness']:
                        data["thickness_raw"] = val
                    elif key == 'weight':
                        data["weight_raw"] = val
                    elif key == 'warranty':
                        data["warranty_raw"] = val
                        
                elif section_name.lower() == 'display':
                    if key == 'size':
                        data["display_size_raw"] = val
                    elif key == 'resolution':
                        data["resolution_raw"] = val
                    elif key == 'ppi':
                        data["ppi_raw"] = val
                    elif key == 'refresh rate':
                        data["refresh_rate_raw"] = val
                    elif key == 'type':
                        data["panel_type_raw"] = val
                    elif key == 'touch':
                        data["touchscreen_raw"] = bool_str
                    elif key == 'anti glare screen':
                        data["anti_glare_raw"] = bool_str
                    elif key == 'features':
                        data["features_raw"] = val
                        
                elif section_name.lower() == 'connectivity':
                    if key in ['wifi', 'wi-fi', 'wlan']:
                        data["wifi_raw"] = val
                    elif key == 'bluetooth':
                        data["bluetooth_raw"] = val
                    elif key == 'usb ports':
                        data["usb_ports_raw"] = val
                    elif key == 'fingerprint sensor':
                        data["fingerprint_sensor_raw"] = bool_str
                        
                elif section_name.lower() == 'input':
                    if key in ['camera', 'webcam']:
                        data["webcam_raw"] = val
                    elif key == 'keyboard backlit':
                        data["backlit_keyboard_raw"] = bool_str
                    elif key in ['microphone', 'inbuilt microphone']:
                        data["microphone_raw"] = bool_str
                        
                elif section_name.lower() == 'processor':
                    if key == 'processor':
                        data["cpu_processor_raw"] = val
                    elif key == 'brand':
                        data["cpu_brand_raw"] = val
                    elif key == 'series':
                        data["cpu_series_raw"] = val
                    elif key == 'model':
                        data["cpu_model_raw"] = val
                    elif key == 'generation':
                        data["cpu_generation_raw"] = val
                    elif key in ['cores', 'core count']:
                        data["cpu_cores_raw"] = val
                    elif key in ['speed', 'clock speed']:
                        data["cpu_speed_raw"] = val
                    elif key == 'cache':
                        data["cpu_cache_raw"] = val
                        
                elif section_name.lower() == 'graphics':
                    if key in ['gpu', 'graphics']:
                        data["gpu_model"] = val
                    elif key == 'brand':
                        data["gpu_brand_raw"] = val
                    elif key in ['dedicated memory', 'dedicated graphics memory', 'vram', 'graphics memory']:
                        data["gpu_vram_raw"] = val
                        
                elif section_name.lower() == 'memory':
                    if key in ['ram', 'system memory']:
                        data["ram_raw"] = val
                    elif key in ['ram bus speed', 'bus speed', 'speed']:
                        data["ram_speed_raw"] = val
                    elif key == 'ram slots':
                        data["ram_slots_raw"] = val
                    elif key in ['maximum ram supported', 'max ram supported']:
                        data["ram_max_raw"] = val
                    elif key in ['solid state drive', 'ssd', 'storage', 'capacity']:
                        data["storage_raw"] = val
                    elif key in ['ssd interface', 'interface']:
                        data["storage_interface_raw"] = val
                        
                elif section_name.lower() == 'battery':
                    if key == 'battery':
                        data["battery_raw"] = val
                    elif key in ['adapter type', 'adapter', 'power adapter']:
                        data["adapter_raw"] = val

        # 3. Fallbacks and conflict checks from product title
        if data["model_name"]:
            title_lower = data["model_name"].lower()
            
            # RAM fallback
            if not data["ram_raw"]:
                ram_match = re.search(r'(\d+)\s*gb\s*ram?', title_lower)
                if ram_match:
                    data["ram_raw"] = ram_match.group(1) + " GB"
                    
            # Storage fallback
            if not data["storage_raw"]:
                storage_match = re.search(r'(\d+)\s*(gb|tb)\s*(?:ssd|hdd)', title_lower)
                if storage_match:
                    data["storage_raw"] = storage_match.group(1) + " " + storage_match.group(2).upper()
                    
            # VRAM fallback
            if not data["gpu_vram_raw"]:
                vram_match = re.search(r'(\d+)\s*gb\s*(?:rtx|gtx|rx|graph)', title_lower)
                if vram_match:
                    data["gpu_vram_raw"] = vram_match.group(1) + " GB"

        # 4. Multi-Store Links & Prices Extraction
        stores = {}
        known_stores = ['amazon', 'flipkart', 'croma', 'reliance', 'tatacliq', 'samsung', 'lenovo', 'hp', 'dell', 'acer', 'asus', 'vijay sales']
        
        def identify_store(tag_or_img, text_candidate=""):
            cand = text_candidate.lower()
            if tag_or_img:
                cand += " " + (tag_or_img.get('alt') or '').lower() + " " + (tag_or_img.get('src') or '').lower()
            for s in known_stores:
                if s in cand:
                    return s.replace(' ', '_')
            return None

        # 4a. Price comparison cards (.sm-pc-item)
        for item in soup.select('.sm-pc-item'):
            img = item.select_one('img')
            name_el = item.select_one('.store-name, .name')
            store_key = identify_store(img, name_el.text if name_el else "")
            
            a_tag = item.find('a', href=True)
            if not a_tag:
                continue
            href = a_tag['href']
            if href.startswith('/'):
                href = 'https://www.smartprix.com' + href
                
            price_val = None
            price_el = item.select_one('.price')
            if price_el:
                p_match = re.search(r'[\d,]+', price_el.text)
                if p_match:
                    price_val = float(p_match.group(0).replace(',', ''))
                    
            is_oos = 'oos' in item.get('class', [])
            if store_key:
                stores[store_key] = {
                    'url': href,
                    'price': price_val,
                    'in_stock': not is_oos
                }

        # 4b. Store strip items (ul.sm-store-strip li)
        for li in soup.select('ul.sm-store-strip li'):
            img = li.select_one('img')
            name_el = li.select_one('.name')
            store_key = identify_store(img, name_el.text if name_el else "")
            a_tag = li.find('a', href=True)
            if not a_tag:
                continue
            href = a_tag['href']
            if href.startswith('/'):
                href = 'https://www.smartprix.com' + href
                
            price_val = None
            price_el = li.select_one('.price')
            if price_el:
                p_match = re.search(r'[\d,]+', price_el.text)
                if p_match:
                    price_val = float(p_match.group(0).replace(',', ''))
                    
            if store_key and store_key not in stores:
                stores[store_key] = {
                    'url': href,
                    'price': price_val,
                    'in_stock': True
                }

        # 4c. Hero section main buy button fallback
        hero_btn = soup.select_one('.pg-prd-pricewrap a.buy-btn, .pg-prd-pricewrap a[href*="l.smartprix.com"]')
        if hero_btn and hero_btn.has_attr('href'):
            img = hero_btn.select_one('img')
            store_key = identify_store(img, hero_btn.text)
            href = hero_btn['href']
            if href.startswith('/'):
                href = 'https://www.smartprix.com' + href
            hero_price_el = soup.select_one('.pg-prd-pricewrap .price')
            hero_price = None
            if hero_price_el:
                p_match = re.search(r'[\d,]+', hero_price_el.text)
                if p_match:
                    hero_price = float(p_match.group(0).replace(',', ''))
            if store_key and store_key not in stores:
                stores[store_key] = {
                    'url': href,
                    'price': hero_price,
                    'in_stock': True
                }

        # Clean simplified mapping: {"amazon": link, "croma": link}
        data["shop_links"] = {k: v["url"] for k, v in stores.items()}
        data["store_details"] = stores

        # Identify lowest available price and best store
        in_stock_stores = {k: v for k, v in stores.items() if v.get("in_stock") and v.get("price")}
        eligible = in_stock_stores if in_stock_stores else {k: v for k, v in stores.items() if v.get("price")}
        if eligible:
            best_k = min(eligible.keys(), key=lambda k: eligible[k]["price"])
            data["best_store"] = best_k
            data["min_store_price"] = eligible[best_k]["price"]

        return data
