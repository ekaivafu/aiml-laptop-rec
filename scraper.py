import typer
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from core.database import init_db, SessionLocal
from core.models import ScrapeJob, Laptop, PriceObservation, RawProduct, LaptopMLFeature
from collectors.smartprix import SmartprixCollector
from pipeline.normalizer import (
    normalize_price, normalize_ram, normalize_storage, extract_float, 
    normalize_battery, normalize_weight, normalize_os, normalize_thickness, 
    normalize_boolean, normalize_display, normalize_cpu, normalize_cores_and_threads, 
    normalize_gpu, extract_integer
)
from pipeline.validator import validate_laptop_data
from pipeline.feature_engineer import compute_ml_features
from pipeline.year_filter import is_laptop_2022_or_newer
from datetime import datetime
import pandas as pd
import json
import os
import sys
import time

# Ensure Windows PowerShell console can output UTF-8 without charmap errors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def safe_echo(msg: str):
    """Safely print messages preventing cp1252 encoding crashes on Windows."""
    try:
        typer.echo(msg)
    except Exception:
        try:
            print(msg.encode('ascii', 'replace').decode('ascii'))
        except Exception:
            pass

app = typer.Typer(help="India Laptop Data Collector & ML Dataset CLI")

@app.command()
def init():
    """Initialize or upgrade the database schema."""
    init_db()
    typer.echo("Database initialized with updated schema.")

def process_raw_to_laptop(db, raw_data: dict, source: str, product_url: str) -> Tuple[Optional[Laptop], str]:
    """Helper to normalize raw specs, upsert Laptop, and generate ML feature entry."""
    norm_price = normalize_price(raw_data.get("price_inr"))
    norm_mrp = normalize_price(raw_data.get("mrp_inr"))
    
    # Calculate discount
    discount_pct = 0.0
    if norm_mrp and norm_price and norm_mrp > norm_price:
        discount_pct = round(((norm_mrp - norm_price) / norm_mrp) * 100.0, 1)

    ram_info = normalize_ram(raw_data.get("ram_raw"), raw_data.get("ram_speed_raw"))
    storage_info = normalize_storage(raw_data.get("storage_raw"))
    display_info = normalize_display(
        raw_data.get("display_size_raw"),
        raw_data.get("resolution_raw"),
        raw_data.get("refresh_rate_raw"),
        raw_data.get("panel_type_raw"),
        raw_data.get("features_raw")
    )
    cpu_info = normalize_cpu(
        raw_data.get("cpu_processor_raw"),
        raw_data.get("cpu_brand_raw"),
        raw_data.get("cpu_series_raw"),
        raw_data.get("cpu_model_raw"),
        raw_data.get("cpu_generation_raw")
    )
    cores_info = normalize_cores_and_threads(
        raw_data.get("cpu_cores_raw"),
        raw_data.get("cpu_speed_raw")
    )
    gpu_info = normalize_gpu(
        raw_data.get("gpu_model"),
        raw_data.get("gpu_vram_raw"),
        raw_data.get("gpu_brand_raw")
    )
    battery_info = normalize_battery(
        raw_data.get("battery_raw"),
        raw_data.get("adapter_raw")
    )
    weight = normalize_weight(raw_data.get("weight_raw"))
    thickness = normalize_thickness(raw_data.get("thickness_raw"))
    os_clean = normalize_os(raw_data.get("os_raw"))
    warranty = extract_integer(raw_data.get("warranty_raw")) or 1

    # -------------------------------------------------------------
    # MULTI-LEVEL DEDUPLICATION
    # -------------------------------------------------------------
    model_name = raw_data.get("model_name")
    model_number = raw_data.get("model_number")
    brand = raw_data.get("brand") or (model_name.split()[0] if model_name else "Unknown")
    cpu_model_clean = cpu_info.get("cpu_model") or raw_data.get("cpu_processor_raw")
    
    # -------------------------------------------------------------
    # 2022+ LAUNCH YEAR FILTER
    # -------------------------------------------------------------
    is_2022_plus, filter_reason = is_laptop_2022_or_newer(
        model_name=model_name,
        cpu_model=cpu_model_clean,
        cpu_brand=cpu_info.get("cpu_brand"),
        cpu_family=cpu_info.get("cpu_family"),
        cpu_generation=cpu_info.get("cpu_generation"),
        raw_specs=raw_data.get("raw_specs")
    )
    if not is_2022_plus:
        return None, filter_reason
    
    laptop = None
    # 1. Match by Brand + Model Number (highest precision)
    if model_number and len(model_number.strip()) >= 3:
        laptop = db.query(Laptop).filter(
            Laptop.brand == brand, 
            Laptop.model_number == model_number.strip()
        ).first()

    # 2. Match by exact Title / Model Name
    if not laptop and model_name:
        laptop = db.query(Laptop).filter(Laptop.model_name == model_name).first()

    # 3. Match by Canonical Hardware Fingerprint (same brand, cpu, ram, storage, gpu dedicated status, screen)
    # Safeguard: Never merge a gaming laptop into an office laptop, and never merge different series
    is_dgpu = bool(gpu_info.get("is_dedicated"))
    series = raw_data.get("series")
    if not laptop and brand and cpu_model_clean and ram_info.get("gb"):
        query = db.query(Laptop).filter(
            Laptop.brand == brand,
            Laptop.cpu_model == cpu_model_clean,
            Laptop.ram_gb == ram_info.get("gb"),
            Laptop.storage_gb == storage_info.get("gb"),
            Laptop.screen_size_in == display_info.get("screen_size_in"),
            Laptop.is_dedicated_gpu == is_dgpu
        )
        if series:
            query = query.filter(Laptop.series == series)
        laptop = query.first()

    if not laptop:
        laptop = Laptop()
        db.add(laptop)

    # Populate Laptop entity
    laptop.brand = brand
    laptop.model_name = model_name
    laptop.series = raw_data.get("series")
    laptop.model_number = model_number
    laptop.device_type = raw_data.get("device_type_raw")
    laptop.utility = raw_data.get("utility_raw")
    laptop.os = os_clean
    laptop.price_inr = norm_price
    laptop.mrp_inr = norm_mrp
    laptop.discount_percent = discount_pct
    laptop.weight_kg = weight
    laptop.thickness_mm = thickness
    laptop.warranty_years = warranty

    # Display
    laptop.screen_size_in = display_info.get("screen_size_in")
    laptop.resolution = display_info.get("resolution_str")
    laptop.resolution_width = display_info.get("resolution_width")
    laptop.resolution_height = display_info.get("resolution_height")
    laptop.refresh_rate_hz = display_info.get("refresh_rate_hz")
    laptop.panel_type = display_info.get("panel_type")
    laptop.ppi = extract_integer(raw_data.get("ppi_raw"))
    laptop.touchscreen = normalize_boolean(raw_data.get("touchscreen_raw"))
    laptop.anti_glare = normalize_boolean(raw_data.get("anti_glare_raw"))
    laptop.brightness_nits = display_info.get("brightness_nits")
    laptop.display_features = raw_data.get("features_raw")

    # CPU
    laptop.cpu_model = cpu_info.get("cpu_model") or raw_data.get("cpu_processor_raw")
    laptop.cpu_brand = cpu_info.get("cpu_brand")
    laptop.cpu_family = cpu_info.get("cpu_family")
    laptop.cpu_generation = cpu_info.get("cpu_generation")
    laptop.cpu_cores = cores_info.get("cores")
    laptop.cpu_threads = cores_info.get("threads")
    laptop.cpu_max_clock_ghz = cores_info.get("max_clock_ghz")
    laptop.is_high_perf_cpu = cpu_info.get("is_high_perf")

    # GPU
    laptop.gpu_model = gpu_info.get("gpu_model")
    laptop.gpu_brand = gpu_info.get("gpu_brand")
    laptop.is_dedicated_gpu = gpu_info.get("is_dedicated")
    laptop.gpu_vram_gb = gpu_info.get("gpu_vram_gb")

    # RAM & Storage
    laptop.ram_gb = ram_info.get("gb")
    laptop.ram_type = ram_info.get("type")
    laptop.ram_speed_mhz = ram_info.get("speed_mhz")
    laptop.storage_gb = storage_info.get("gb")
    laptop.storage_type = storage_info.get("type")

    # Hardware & Connectivity
    laptop.wifi_version = raw_data.get("wifi_raw")[:100] if raw_data.get("wifi_raw") else None
    laptop.bluetooth_version = raw_data.get("bluetooth_raw")[:100] if raw_data.get("bluetooth_raw") else None
    laptop.usb_ports = extract_integer(raw_data.get("usb_ports_raw"))
    laptop.webcam = raw_data.get("webcam_raw")
    laptop.fingerprint_sensor = normalize_boolean(raw_data.get("fingerprint_sensor_raw"))
    laptop.backlit_keyboard = normalize_boolean(raw_data.get("backlit_keyboard_raw"))
    laptop.microphone = normalize_boolean(raw_data.get("microphone_raw"))
    laptop.battery_wh = battery_info.get("battery_wh")
    laptop.charger_w = battery_info.get("charger_w")
    laptop.raw_specs = raw_data.get("raw_specs")

    # Store Information & Deal Prices
    shop_links = raw_data.get("shop_links") or {}
    store_details = raw_data.get("store_details") or {}
    min_store_price = raw_data.get("min_store_price") or norm_price
    best_store = raw_data.get("best_store") or ("smartprix" if not shop_links else list(shop_links.keys())[0])

    laptop.best_store = best_store
    laptop.image_url = raw_data.get("image_url")
    laptop.shop_links = shop_links
    laptop.store_details = store_details

    db.flush() # Ensure laptop has an id

    # Record price observation for main product
    if norm_price:
        obs = PriceObservation(
            laptop_id=laptop.id,
            source=source,
            seller=best_store,
            price_inr=norm_price,
            mrp_inr=norm_mrp,
            availability=raw_data.get("availability"),
            product_url=product_url
        )
        db.add(obs)

    # Record individual store observations
    if isinstance(store_details, dict):
        for s_name, s_info in store_details.items():
            s_price = s_info.get("price")
            s_url = s_info.get("url") or product_url
            if s_price and s_price != norm_price:
                s_obs = PriceObservation(
                    laptop_id=laptop.id,
                    source=source,
                    seller=s_name,
                    price_inr=s_price,
                    mrp_inr=norm_mrp,
                    availability="InStock" if s_info.get("in_stock") else "OutOfStock",
                    product_url=s_url
                )
                db.add(s_obs)

    # Compute and upsert Tier-3 ML Features
    ml_feature = compute_ml_features(laptop)
    existing_ml = db.query(LaptopMLFeature).filter(LaptopMLFeature.laptop_id == laptop.id).first()
    if existing_ml:
        for col in ml_feature.__table__.columns:
            if col.name not in ['id', 'laptop_id', 'created_at']:
                setattr(existing_ml, col.name, getattr(ml_feature, col.name))
    else:
        db.add(ml_feature)

    return laptop, "Success"

@app.command()
def discover(source: str = "smartprix", limit: int = 50, start_page: int = 1):
    """Discover product URLs and add them to the queue."""
    db = SessionLocal()
    
    if source == "smartprix":
        collector = SmartprixCollector()
    else:
        typer.echo(f"Source {source} not supported yet.")
        return
        
    typer.echo(f"Discovering up to {limit} URLs from {source} starting at page {start_page}...")
    urls = collector.discover_urls(limit=limit, start_page=start_page)
    
    new_jobs = 0
    for url in urls:
        existing = db.query(ScrapeJob).filter(ScrapeJob.url == url).first()
        if not existing:
            job = ScrapeJob(url=url, source=source)
            db.add(job)
            new_jobs += 1
            
    db.commit()
    typer.echo(f"Discovered {len(urls)} URLs. Added {new_jobs} new jobs to the queue.")

@app.command()
def scrape(limit: int = 2000, delay: float = 0.2, workers: int = 6):
    """Process pending jobs from the queue with concurrent scraping, polite delay, and 2022+ validation."""
    db = SessionLocal()
    
    # -------------------------------------------------------------
    # CRASH RECOVERY: Reset jobs that were interrupted mid-scrape
    # -------------------------------------------------------------
    interrupted = db.query(ScrapeJob).filter(ScrapeJob.status == "processing").all()
    if interrupted:
        for j in interrupted:
            j.status = "pending"
        db.commit()
        typer.echo(f"🔄 Auto-recovered {len(interrupted)} interrupted job(s) from previous session.")

    pending_jobs = db.query(ScrapeJob.id).filter(ScrapeJob.status == "pending").limit(limit).all()
    pending_ids = [j[0] for j in pending_jobs]
    db.close()
    
    if not pending_ids:
        typer.echo("No pending jobs found in queue.")
        return
        
    typer.echo(f"Processing {len(pending_ids)} jobs using {workers} concurrent workers (delay: {delay}s)...")
    
    def process_job_worker(job_id: int):
        t_db = SessionLocal()
        try:
            job = t_db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
            if not job or job.status != "pending":
                return False, "Already processed"
                
            job.status = "processing"
            job.attempt_count += 1
            job.last_attempt = datetime.now()
            t_db.commit()
            
            collector = SmartprixCollector()
            html, json_data = collector.fetch_product(job.url)
            if not html and not json_data:
                raise Exception("Empty response from website")
                
            raw_data = collector.extract_raw_fields(html, json_data)
            
            # Save Raw Product
            raw_product = RawProduct(
                source=job.source,
                product_url=job.url,
                raw_html=html
            )
            t_db.add(raw_product)
            t_db.commit()
            
            # Auto-harvest related product URLs to keep the queue rich
            if html:
                try:
                    soup = BeautifulSoup(html, 'html.parser')
                    related = [
                        a.get('href') for a in soup.find_all('a', href=True)
                        if '-ppd' in a.get('href', '') and '/laptops/' in a.get('href', '')
                    ]
                    for href in related:
                        full_url = "https://www.smartprix.com" + href if href.startswith('/') else href
                        exists = t_db.query(ScrapeJob.id).filter(ScrapeJob.url == full_url).first()
                        if not exists:
                            t_db.add(ScrapeJob(url=full_url, source=job.source))
                    t_db.commit()
                except Exception:
                    pass
            
            laptop, reason = process_raw_to_laptop(t_db, raw_data, job.source, job.url)
            if laptop:
                raw_product.laptop_id = laptop.id
                job.status = "completed"
                job.error_reason = None
                t_db.commit()
                if delay > 0:
                    time.sleep(delay)
                return True, f"Saved: {laptop.brand} {laptop.model_name[:35]} (Rs. {laptop.price_inr})"
            else:
                job.status = "completed"
                job.error_reason = f"skipped_pre_2022: {reason}"
                t_db.commit()
                if delay > 0:
                    time.sleep(delay)
                return True, f"Skipped (Pre-2022): {raw_data.get('model_name', job.url)[:35]} ({reason})"
                
        except Exception as e:
            t_db.rollback()
            try:
                job = t_db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                if job:
                    job.status = "failed"
                    job.error_reason = str(e)[:250]
                    t_db.commit()
            except Exception:
                pass
            return False, f"Failed job {job_id}: {e}"
        finally:
            t_db.close()

    success_count = 0
    total = len(pending_ids)
    done_count = 0
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_job_worker, jid): jid for jid in pending_ids}
        for future in as_completed(futures):
            done_count += 1
            ok, msg = future.result()
            if ok:
                success_count += 1
            if done_count % 25 == 0 or done_count == total:
                safe_echo(f"[{done_count}/{total}] {msg}")
            
    safe_echo(f"\nScraping batch finished. Processed: {success_count}/{total} jobs.")

@app.command()
def reparse():
    """Reprocess all saved raw products with the latest parser without hitting the web."""
    db = SessionLocal()
    raw_prods = db.query(RawProduct).all()
    if not raw_prods:
        typer.echo("No raw products found in database to reparse.")
        return
        
    typer.echo(f"Reparsing {len(raw_prods)} raw products with 2022+ validator...")
    collector = SmartprixCollector()
    
    count = 0
    skipped = 0
    for rp in raw_prods:
        try:
            raw_data = collector.extract_raw_fields(rp.raw_html, rp.raw_json)
            laptop, reason = process_raw_to_laptop(db, raw_data, rp.source, rp.product_url)
            if laptop:
                rp.laptop_id = laptop.id
                db.commit()
                count += 1
                typer.echo(f"[{count}/{len(raw_prods)}] Parsed: {laptop.brand} {laptop.model_name[:40]} -> Rs. {laptop.price_inr}")
            else:
                if rp.laptop_id:
                    db.query(LaptopMLFeature).filter(LaptopMLFeature.laptop_id == rp.laptop_id).delete()
                    db.query(PriceObservation).filter(PriceObservation.laptop_id == rp.laptop_id).delete()
                    db.query(Laptop).filter(Laptop.id == rp.laptop_id).delete()
                    rp.laptop_id = None
                    db.commit()
                skipped += 1
                typer.echo(f"Skipped pre-2022: {raw_data.get('model_name', rp.product_url)[:40]} ({reason})")
        except Exception as e:
            db.rollback()
            typer.echo(f"Error reparsing raw product {rp.id}: {e}")
            
    typer.echo(f"Reparsing complete! Updated {count} laptops, skipped {skipped} pre-2022 laptops.")

@app.command()
def export():
    """Export both full catalog and sanitized ML feature datasets (CSV & Parquet)."""
    db = SessionLocal()
    exports_dir = os.path.join("data", "exports")
    os.makedirs(exports_dir, exist_ok=True)
    
    # 1. Export Full Catalog
    laptops = db.query(Laptop).all()
    if not laptops:
        typer.echo("No laptops found to export.")
        return
        
    catalog_data = []
    for l in laptops:
        l_dict = {}
        for c in l.__table__.columns:
            if c.name in ["raw_specs", "created_at", "updated_at"]:
                continue
            val = getattr(l, c.name)
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            l_dict[c.name] = val
        catalog_data.append(l_dict)
        
    df_catalog = pd.DataFrame(catalog_data)
    catalog_csv = os.path.join(exports_dir, "laptops.csv")
    df_catalog.to_csv(catalog_csv, index=False)
    typer.echo(f"Exported {len(df_catalog)} catalog laptops to {catalog_csv}")
    
    # 2. Export Sanitized ML Training Dataset
    ml_features = db.query(LaptopMLFeature).all()
    if ml_features:
        ml_data = []
        for m in ml_features:
            m_dict = {
                c.name: getattr(m, c.name)
                for c in m.__table__.columns
                if c.name not in ["id", "created_at"]
            }
            ml_data.append(m_dict)
            
        df_ml = pd.DataFrame(ml_data)
        ml_csv = os.path.join(exports_dir, "laptops_ml_ready.csv")
        ml_parquet = os.path.join(exports_dir, "laptops_ml_ready.parquet")
        
        df_ml.to_csv(ml_csv, index=False)
        df_ml.to_parquet(ml_parquet, index=False)
        typer.echo(f"Exported {len(df_ml)} ML feature records to {ml_csv} and {ml_parquet}")

@app.command()
def status():
    """Display queue statistics, total unique laptops collected, and status counts."""
    db = SessionLocal()
    total_jobs = db.query(ScrapeJob).count()
    pending = db.query(ScrapeJob).filter(ScrapeJob.status == "pending").count()
    processing = db.query(ScrapeJob).filter(ScrapeJob.status == "processing").count()
    completed = db.query(ScrapeJob).filter(ScrapeJob.status == "completed").count()
    failed = db.query(ScrapeJob).filter(ScrapeJob.status == "failed").count()
    
    unique_laptops = db.query(Laptop).count()
    raw_saved = db.query(RawProduct).count()
    
    typer.echo("\n" + "=" * 45)
    typer.echo("         DATA PIPELINE STATUS")
    typer.echo("=" * 45)
    typer.echo(f"  Total URLs in Queue:  {total_jobs}")
    typer.echo(f"    - Pending:          {pending}")
    typer.echo(f"    - In-Progress:      {processing}")
    typer.echo(f"    - Completed:        {completed}")
    typer.echo(f"    - Failed:           {failed}")
    typer.echo("-" * 45)
    typer.echo(f"  Raw HTMLs Cached:     {raw_saved}")
    typer.echo(f"  Unique Laptops:       {unique_laptops}")
    typer.echo("=" * 45 + "\n")

@app.command()
def retry_failed():
    """Reset all failed jobs back to pending to re-attempt scraping."""
    db = SessionLocal()
    failed_jobs = db.query(ScrapeJob).filter(ScrapeJob.status == "failed").all()
    if not failed_jobs:
        typer.echo("No failed jobs to retry.")
        return
    for j in failed_jobs:
        j.status = "pending"
    db.commit()
    typer.echo(f"Reset {len(failed_jobs)} failed job(s) back to pending queue.")

if __name__ == "__main__":
    app()
