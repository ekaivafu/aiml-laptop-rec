"""Tests for recommender.py catalog loading, filtering, and ranking."""

import io
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from recommender import (
    load_catalog,
    filter_catalog,
    recommend,
    format_inr,
    format_specs_line,
    get_listing_url,
    generate_match_reason,
)


@pytest.fixture
def sample_catalog_csv(tmp_path: Path) -> Path:
    """Fixture providing a clean catalog CSV."""
    csv_content = """id,brand,model_name,price_inr,ram_gb,storage_gb,cpu_model,gpu_model,is_dedicated_gpu,gpu_vram_gb,weight_kg,shop_links
1,Lenovo,Lenovo IdeaPad Slim 3,45000,16,512,Core i5,Integrated,0,0,1.43,"{\\"amazon\\": \\"https://amazon.in/dp/B01\\"}"
2,HP,HP Victus 15,60000,16,512,Ryzen 5,RTX 2050,1,4,2.29,"{\\"flipkart\\": \\"https://flipkart.com/p/1\\"}"
3,Acer,Acer Nitro V,75000,16,512,Core i5,RTX 4050,1,6,2.1,"https://store.acer.com/p/2"
4,Apple,MacBook Air M2,85000,8,256,Apple M2,Apple 8-core GPU,0,0,1.24,""
5,Asus,Asus ROG Strix,95000,16,1024,Core i7,RTX 4060,1,8,2.5,""
"""
    file_path = tmp_path / "laptops.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_features_csv(tmp_path: Path) -> Path:
    """Fixture providing a clean features CSV corresponding to sample_catalog_csv."""
    csv_content = """laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money
1,0.88,35.0,25.0,40.0,60.0,85.0,88.0,80.0
2,0.88,68.0,60.0,65.0,70.0,60.0,45.0,75.0
3,1.00,85.0,80.0,82.0,80.0,55.0,40.0,85.0
4,0.75,30.0,45.0,60.0,72.0,90.0,95.0,60.0
5,1.00,92.0,88.0,90.0,88.0,50.0,35.0,70.0
"""
    file_path = tmp_path / "laptops_ml_ready.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    return file_path


# 1. Padded headers
def test_load_catalog_padded_headers(tmp_path: Path):
    cat = "  id  ,  brand  , model_name , price_inr \n10,Dell,Dell XPS 13,90000\n"
    feat = " laptop_id , score_confidence , score_gaming , score_aiml , score_video_editing , score_programming , score_student_office , score_portability , score_value_for_money \n10,1.0,50,50,50,50,50,50,50\n"
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    cp.write_text(cat)
    fp.write_text(feat)

    df = load_catalog(cp, fp)
    assert len(df) == 1
    assert "id" in df.columns
    assert "score_gaming" in df.columns
    assert df.iloc[0]["brand"] == "Dell"


# 2. Missing files or required columns
def test_load_catalog_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_catalog(tmp_path / "nonexistent.csv", tmp_path / "features.csv")


def test_load_catalog_missing_required_columns(tmp_path: Path):
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    # Catalog missing price_inr
    cp.write_text("id,brand,model_name\n1,HP,Victus\n")
    fp.write_text("laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money\n1,1,50,50,50,50,50,50,50\n")

    with pytest.raises(ValueError, match="Catalog dataset missing required columns"):
        load_catalog(cp, fp)


# 3. Duplicate or unmatched IDs
def test_load_catalog_duplicate_ids(tmp_path: Path):
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    # Duplicate ID 1 in catalog
    cp.write_text("id,brand,model_name,price_inr\n1,HP,Victus,50000\n1,HP,Pavilion,40000\n")
    fp.write_text("laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money\n1,1,50,50,50,50,50,50,50\n")

    with pytest.raises(ValueError, match="Duplicate id found in catalog data"):
        load_catalog(cp, fp)


def test_load_catalog_unmatched_ids(tmp_path: Path):
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    cp.write_text("id,brand,model_name,price_inr\n1,HP,Victus,50000\n2,Lenovo,IdeaPad,40000\n")
    fp.write_text("laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money\n1,1,50,50,50,50,50,50,50\n3,1,50,50,50,50,50,50,50\n")

    with pytest.raises(ValueError, match="Mismatch between catalog ids and features"):
        load_catalog(cp, fp)


# 4. Unknown catalog price with an imputed feature price
def test_unknown_catalog_price_excluded(tmp_path: Path):
    # Catalog has NaN price, while features might have imputed 55000
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    cp.write_text("id,brand,model_name,price_inr\n1,HP,Victus,\n2,Lenovo,Slim,50000\n")
    fp.write_text("laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money\n1,0.5,50,50,50,50,50,50,50\n2,1.0,50,50,50,50,50,50,50\n")

    df = load_catalog(cp, fp)
    # The loaded df preserves NaN catalog price
    assert pd.isna(df.loc[df["id"] == 1, "price_inr"].values[0])

    # When filtering with budget 60000, laptop 1 with NaN catalog price MUST be excluded!
    filtered = filter_catalog(df, budget=60000)
    assert len(filtered) == 1
    assert filtered.iloc[0]["id"] == 2


# 5. Exact budget inclusion
def test_exact_budget_included(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Laptop 2 has price_inr = 60000
    filtered = filter_catalog(df, budget=60000)
    assert 2 in filtered["id"].values
    assert 1 in filtered["id"].values  # 45000 <= 60000


# 6. Over-budget exclusion
def test_over_budget_excluded(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Budget 60000 excludes laptops with prices 75000, 85000, 95000 (IDs 3, 4, 5)
    filtered = filter_catalog(df, budget=60000)
    assert not any(id_val in filtered["id"].values for id_val in [3, 4, 5])
    assert set(filtered["id"].values) == {1, 2}


# 7. Combined filters
def test_combined_filters(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Budget 90000, brand in ('HP', 'Acer'), min_ram 16, min_storage 512
    filtered = filter_catalog(
        df,
        budget=90000,
        brands=("HP", "Acer"),
        min_ram_gb=16,
        min_storage_gb=512,
    )
    # IDs 2 (HP: 60k, 16gb, 512gb) and 3 (Acer: 75k, 16gb, 512gb) should pass
    # Lenovo is not in brands, Apple has 8gb RAM and 256gb storage, Asus is 95k
    assert set(filtered["id"].values) == {2, 3}


# 8. Missing specs with and without an active minimum
def test_missing_specs_with_and_without_active_minimum(tmp_path: Path):
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    # Laptop 1 has missing RAM (NaN), Laptop 2 has 16GB
    cp.write_text("id,brand,model_name,price_inr,ram_gb,storage_gb\n1,HP,Victus,50000,,512\n2,Lenovo,Slim,50000,16,512\n")
    fp.write_text("laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money\n1,0.5,50,50,50,50,50,50,50\n2,1.0,50,50,50,50,50,50,50\n")

    df = load_catalog(cp, fp)

    # Without active RAM filter: laptop 1 passes
    f_no_ram = filter_catalog(df, budget=60000, min_ram_gb=None)
    assert len(f_no_ram) == 2

    # With active RAM filter: laptop 1 fails (missing spec fails when filter active)
    f_with_ram = filter_catalog(df, budget=60000, min_ram_gb=8)
    assert len(f_with_ram) == 1
    assert f_with_ram.iloc[0]["id"] == 2


# 9. Switch in ranking when the use case changes
def test_switch_in_ranking_on_use_case_change(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Laptops 1 and 2 are within 60000 budget
    eligible = filter_catalog(df, budget=60000)

    # For student-office: laptop 1 has score_student_office 85 vs laptop 2's 60
    rec_office = recommend(eligible, use_case="student-office", top=2)
    assert rec_office.iloc[0]["id"] == 1

    # For gaming: laptop 2 has score_gaming 68 vs laptop 1's 35
    rec_gaming = recommend(eligible, use_case="gaming", top=2)
    assert rec_gaming.iloc[0]["id"] == 2


# 10. Deterministic ties
def test_deterministic_ties(tmp_path: Path):
    cp = tmp_path / "c.csv"
    fp = tmp_path / "f.csv"
    # Three laptops with identical scores, different confidence, prices, and IDs
    cp.write_text("""id,brand,model_name,price_inr,ram_gb,storage_gb
10,A,LapA,50000,16,512
20,B,LapB,50000,16,512
30,C,LapC,45000,16,512
40,D,LapD,45000,16,512
""")
    # Lap 10 and 20: identical distance, Lap 10 has higher confidence (0.9 vs 0.8) -> Lap 10 before 20
    # Lap 30 and 40: identical distance, identical confidence (0.8), identical price (45000) -> Lap 30 before 40 (numeric id 30 < 40)
    # Lap 30 has lower price (45000 vs 50000 for 20) with same confidence -> Lap 30 before 20
    fp.write_text("""laptop_id,score_confidence,score_gaming,score_aiml,score_video_editing,score_programming,score_student_office,score_portability,score_value_for_money
10,0.9,80,80,80,80,80,80,80
20,0.8,80,80,80,80,80,80,80
30,0.8,80,80,80,80,80,80,80
40,0.8,80,80,80,80,80,80,80
""")
    df = load_catalog(cp, fp)
    rec = recommend(df, use_case="gaming", top=4)

    # 1. Distance are all identical (same score 80).
    # 2. Confidence: id 10 has 0.9, others have 0.8 -> id 10 must be first.
    # 3. Among 20, 30, 40 (conf 0.8):
    #    id 30 and 40 have price 45000 < 50000 (id 20) -> 30 and 40 come before 20.
    # 4. Between 30 and 40 (same conf 0.8, same price 45000): numeric id 30 < 40 -> 30 before 40.
    # Expected order: 10, 30, 40, 20
    assert list(rec["id"]) == [10, 30, 40, 20]


# 11. Fewer matches than requested
def test_fewer_matches_than_requested(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Budget 50000 has only 1 laptop (id 1, price 45000)
    eligible = filter_catalog(df, budget=50000)
    assert len(eligible) == 1

    rec = recommend(eligible, use_case="student-office", top=5)
    assert len(rec) == 1
    assert rec.iloc[0]["id"] == 1


# 12. No matches
def test_no_matches_returns_empty_frame(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    # Budget 20000 matches nothing in sample catalog
    eligible = filter_catalog(df, budget=20000)
    assert eligible.empty

    rec = recommend(eligible, use_case="gaming", top=5)
    assert rec.empty
    assert isinstance(rec, pd.DataFrame)


# Value use case
def test_recommend_value_use_case(sample_catalog_csv: Path, sample_features_csv: Path):
    df = load_catalog(sample_catalog_csv, sample_features_csv)
    rec = recommend(df, use_case="value", top=3)
    assert len(rec) == 3
    # Acer (id 3) has highest score_value_for_money (85.0), then Lenovo (id 1) 80.0
    assert rec.iloc[0]["id"] == 3


# Formatting helpers
def test_format_inr():
    assert format_inr(79990) == "₹79,990"
    assert format_inr(60000) == "₹60,000"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(1250000) == "₹12,50,000"
    assert format_inr(None) == "N/A"


def test_get_listing_url():
    json_links = '{"flipkart": "https://flipkart.com/item1", "amazon": "https://amazon.in/item1"}'
    assert get_listing_url(json_links, best_store="flipkart") == "https://flipkart.com/item1"
    assert get_listing_url(json_links, best_store="croma") == "https://flipkart.com/item1"
    assert get_listing_url("https://direct.com/laptop") == "https://direct.com/laptop"
    assert get_listing_url(None) is None


def test_format_specs_line():
    row = {
        "cpu_model": "Core i5 13th Gen",
        "gpu_model": "RTX 4050",
        "ram_gb": 16,
        "storage_gb": 512,
    }
    specs = format_specs_line(row)
    assert "Core i5 13th Gen" in specs
    assert "RTX 4050" in specs
    assert "16 GB RAM" in specs
    assert "512 GB SSD" in specs


def test_generate_match_reason():
    row = {
        "is_dedicated_gpu": True,
        "gpu_model": "RTX 4050",
        "ram_gb": 16,
        "cpu_model": "Core i5",
        "weight_kg": 2.1,
    }
    reason = generate_match_reason(row, "gaming")
    assert "Dedicated graphics" in reason
    assert "16 GB RAM" in reason
