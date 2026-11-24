from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed, retry
    attempt_count: Mapped[int] = mapped_column(default=0)
    last_attempt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

class Laptop(Base):
    __tablename__ = "laptops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # General & Price
    brand: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    series: Mapped[Optional[str]] = mapped_column(String(100))
    model_number: Mapped[Optional[str]] = mapped_column(String(100))
    device_type: Mapped[Optional[str]] = mapped_column(String(100))
    utility: Mapped[Optional[str]] = mapped_column(String(255))
    os: Mapped[Optional[str]] = mapped_column(String(100))
    price_inr: Mapped[Optional[float]] = mapped_column(Float, index=True)
    mrp_inr: Mapped[Optional[float]] = mapped_column(Float)
    discount_percent: Mapped[Optional[float]] = mapped_column(Float)
    best_store: Mapped[Optional[str]] = mapped_column(String(50))
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    shop_links: Mapped[Optional[dict]] = mapped_column(JSON)
    store_details: Mapped[Optional[dict]] = mapped_column(JSON)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    thickness_mm: Mapped[Optional[float]] = mapped_column(Float)
    warranty_years: Mapped[Optional[int]] = mapped_column(Integer)

    # Display
    screen_size_in: Mapped[Optional[float]] = mapped_column(Float)
    resolution: Mapped[Optional[str]] = mapped_column(String(100))
    resolution_width: Mapped[Optional[int]] = mapped_column(Integer)
    resolution_height: Mapped[Optional[int]] = mapped_column(Integer)
    refresh_rate_hz: Mapped[Optional[int]] = mapped_column(Integer, default=60)
    panel_type: Mapped[Optional[str]] = mapped_column(String(50))
    ppi: Mapped[Optional[int]] = mapped_column(Integer)
    touchscreen: Mapped[Optional[bool]] = mapped_column(Boolean)
    anti_glare: Mapped[Optional[bool]] = mapped_column(Boolean)
    brightness_nits: Mapped[Optional[int]] = mapped_column(Integer)
    display_features: Mapped[Optional[str]] = mapped_column(Text)

    # Performance - CPU
    cpu_model: Mapped[Optional[str]] = mapped_column(String(255))
    cpu_brand: Mapped[Optional[str]] = mapped_column(String(50))
    cpu_family: Mapped[Optional[str]] = mapped_column(String(100))
    cpu_generation: Mapped[Optional[int]] = mapped_column(Integer)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer)
    cpu_threads: Mapped[Optional[int]] = mapped_column(Integer)
    cpu_max_clock_ghz: Mapped[Optional[float]] = mapped_column(Float)
    is_high_perf_cpu: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Performance - GPU
    gpu_model: Mapped[Optional[str]] = mapped_column(String(255))
    gpu_brand: Mapped[Optional[str]] = mapped_column(String(50))
    is_dedicated_gpu: Mapped[Optional[bool]] = mapped_column(Boolean)
    gpu_vram_gb: Mapped[Optional[float]] = mapped_column(Float)

    # Performance - RAM & Storage
    ram_gb: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    ram_type: Mapped[Optional[str]] = mapped_column(String(50))
    ram_speed_mhz: Mapped[Optional[int]] = mapped_column(Integer)
    storage_gb: Mapped[Optional[int]] = mapped_column(Integer)
    storage_type: Mapped[Optional[str]] = mapped_column(String(100))

    # Connectivity & Hardware
    wifi_version: Mapped[Optional[str]] = mapped_column(String(100))
    bluetooth_version: Mapped[Optional[str]] = mapped_column(String(100))
    usb_ports: Mapped[Optional[int]] = mapped_column(Integer)
    webcam: Mapped[Optional[str]] = mapped_column(String(100))
    fingerprint_sensor: Mapped[Optional[bool]] = mapped_column(Boolean)
    backlit_keyboard: Mapped[Optional[bool]] = mapped_column(Boolean)
    microphone: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Battery
    battery_wh: Mapped[Optional[float]] = mapped_column(Float)
    charger_w: Mapped[Optional[int]] = mapped_column(Integer)

    # Raw Data
    raw_specs: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    price_observations: Mapped[List["PriceObservation"]] = relationship(back_populates="laptop", cascade="all, delete-orphan")
    raw_products: Mapped[List["RawProduct"]] = relationship(back_populates="laptop")
    ml_feature: Mapped[Optional["LaptopMLFeature"]] = relationship(back_populates="laptop", uselist=False, cascade="all, delete-orphan")

class PriceObservation(Base):
    __tablename__ = "price_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    laptop_id: Mapped[int] = mapped_column(ForeignKey("laptops.id"), index=True)
    source: Mapped[str] = mapped_column(String(50))
    seller: Mapped[Optional[str]] = mapped_column(String(100))
    price_inr: Mapped[Optional[float]] = mapped_column(Float)
    mrp_inr: Mapped[Optional[float]] = mapped_column(Float)
    availability: Mapped[Optional[str]] = mapped_column(String(50))
    product_url: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    laptop: Mapped["Laptop"] = relationship(back_populates="price_observations")

class RawProduct(Base):
    __tablename__ = "raw_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    laptop_id: Mapped[Optional[int]] = mapped_column(ForeignKey("laptops.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(50))
    product_url: Mapped[str] = mapped_column(String(500))
    raw_html: Mapped[Optional[str]] = mapped_column(Text)
    raw_json: Mapped[Optional[str]] = mapped_column(Text)
    scraped_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    laptop: Mapped[Optional["Laptop"]] = relationship(back_populates="raw_products")

class LaptopMLFeature(Base):
    """
    Tier-3: Sanitized, strictly numerical & encoded input table for ML models and recommenders.
    """
    __tablename__ = "ml_laptop_features"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    laptop_id: Mapped[int] = mapped_column(ForeignKey("laptops.id"), unique=True, index=True)

    # Identifiers & Market
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    brand: Mapped[str] = mapped_column(String(50), index=True)
    price_inr: Mapped[float] = mapped_column(Float, index=True)
    best_store: Mapped[str] = mapped_column(String(50), default="smartprix")
    store_count: Mapped[int] = mapped_column(Integer, default=1)
    has_amazon: Mapped[bool] = mapped_column(Boolean, default=False)
    has_croma: Mapped[bool] = mapped_column(Boolean, default=False)
    has_flipkart: Mapped[bool] = mapped_column(Boolean, default=False)
    shop_links: Mapped[str] = mapped_column(Text, default="{}") # JSON-serialized mapping: {"amazon": link, "croma": link}
    os: Mapped[str] = mapped_column(String(30))

    # Compute Features
    cpu_brand: Mapped[str] = mapped_column(String(30))
    cpu_tier: Mapped[int] = mapped_column(Integer) # 1 (Entry) to 5 (Flagship)
    cpu_cores: Mapped[int] = mapped_column(Integer)
    cpu_threads: Mapped[int] = mapped_column(Integer)
    cpu_perf_cores: Mapped[int] = mapped_column(Integer)
    cpu_max_ghz: Mapped[float] = mapped_column(Float)
    is_high_perf_cpu: Mapped[bool] = mapped_column(Boolean)

    # Graphics Features
    has_dedicated_gpu: Mapped[bool] = mapped_column(Boolean, index=True)
    gpu_brand: Mapped[str] = mapped_column(String(30))
    gpu_tier: Mapped[int] = mapped_column(Integer) # 0 to 5
    gpu_vram_gb: Mapped[float] = mapped_column(Float)

    # Memory & Storage
    ram_gb: Mapped[int] = mapped_column(Integer, index=True)
    ram_type: Mapped[str] = mapped_column(String(20))
    ram_speed_mhz: Mapped[int] = mapped_column(Integer)
    storage_gb: Mapped[int] = mapped_column(Integer)
    is_ssd: Mapped[bool] = mapped_column(Boolean)

    # Display
    screen_size_in: Mapped[float] = mapped_column(Float)
    resolution_width: Mapped[int] = mapped_column(Integer)
    resolution_height: Mapped[int] = mapped_column(Integer)
    refresh_rate_hz: Mapped[int] = mapped_column(Integer)
    is_oled: Mapped[bool] = mapped_column(Boolean)
    brightness_nits: Mapped[int] = mapped_column(Integer)
    is_touchscreen: Mapped[bool] = mapped_column(Boolean)
    is_anti_glare: Mapped[bool] = mapped_column(Boolean)

    # Mobility & Form Factor
    weight_kg: Mapped[float] = mapped_column(Float)
    thickness_mm: Mapped[float] = mapped_column(Float)
    battery_wh: Mapped[float] = mapped_column(Float)

    # Target Recommendation & Use-Case Scores (0.0 - 100.0)
    score_gaming: Mapped[float] = mapped_column(Float)
    score_aiml: Mapped[float] = mapped_column(Float)
    score_video_editing: Mapped[float] = mapped_column(Float)
    score_programming: Mapped[float] = mapped_column(Float)
    score_student_office: Mapped[float] = mapped_column(Float)
    score_portability: Mapped[float] = mapped_column(Float)
    score_value_for_money: Mapped[float] = mapped_column(Float)

    # Specification Completeness & Reliability Indicator (0.0 - 1.0)
    score_confidence: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    laptop: Mapped["Laptop"] = relationship(back_populates="ml_feature")
