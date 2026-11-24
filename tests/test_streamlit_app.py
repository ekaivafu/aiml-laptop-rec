"""Tests for Streamlit Laptop Finder Webpage using Streamlit AppTest.

Verifies the direct-entry preferences screen, search workflows,
hard budget caps, filter editing, and zero-match states.
"""

import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

# Set test environment indicator so matching delay is skipped in tests
os.environ["PYTEST_CURRENT_TEST"] = "1"

APP_PATH = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def test_preferences_screen_renders_directly_without_landing_page():
    """Verify app renders the search/preferences interface directly upon load."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()
    assert not at.exception
    assert at.session_state["screen"] == "preferences"

    # Verify no landing page button exists
    btn_start = [b for b in at.button if b.key == "btn_get_started"]
    assert len(btn_start) == 0

    # Verify the search form controls are immediately present
    sb_budget = [s for s in at.selectbox if s.key == "pref_budget"]
    sb_use = [s for s in at.selectbox if s.key == "pref_use_case"]
    btn_find = [b for b in at.button if b.key == "btn_find_laptops"]

    assert len(sb_budget) == 1
    assert len(sb_use) == 1
    assert len(btn_find) == 1


def test_search_student_office_60k():
    """Verify ₹60,000 Student / Office search returns matches within budget."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()

    # Configure filters directly
    sb_budget = [s for s in at.selectbox if s.key == "pref_budget"][0]
    sb_use = [s for s in at.selectbox if s.key == "pref_use_case"][0]
    sb_budget.select("₹60,000")
    sb_use.select("Student / Office")

    # Submit
    at.button(key="btn_find_laptops").click().run()

    assert not at.exception
    assert at.session_state["screen"] == "recommendations"
    results = at.session_state["results"]
    assert len(results) > 0
    assert len(results) <= 5

    # Check hard budget cap
    for _, row in results.iterrows():
        assert row["price_inr"] <= 60000


def test_search_gaming_90k():
    """Verify ₹90,000 Gaming search returns matches within budget."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()

    sb_budget = [s for s in at.selectbox if s.key == "pref_budget"][0]
    sb_use = [s for s in at.selectbox if s.key == "pref_use_case"][0]
    sb_budget.select("₹90,000")
    sb_use.select("Gaming")

    at.button(key="btn_find_laptops").click().run()

    assert not at.exception
    assert at.session_state["screen"] == "recommendations"
    results = at.session_state["results"]
    assert len(results) > 0
    for _, row in results.iterrows():
        assert row["price_inr"] <= 90000


def test_edit_filters_preserves_selections_and_resubmits():
    """Verify clicking 'Edit filters' returns to form with previous selections filled in."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()

    sb_budget = [s for s in at.selectbox if s.key == "pref_budget"][0]
    sb_use = [s for s in at.selectbox if s.key == "pref_use_case"][0]
    sb_ram = [s for s in at.selectbox if s.key == "pref_min_ram"][0]
    sb_storage = [s for s in at.selectbox if s.key == "pref_min_storage"][0]

    sb_budget.select("₹80,000")
    sb_use.select("Programming")
    sb_ram.select("16 GB")
    sb_storage.select("512 GB")

    at.button(key="btn_find_laptops").click().run()
    assert at.session_state["screen"] == "recommendations"

    # Click "Edit filters"
    at.button(key="btn_edit_filters").click().run()
    assert at.session_state["screen"] == "preferences"

    # Verify selections were preserved
    sb_budget2 = [s for s in at.selectbox if s.key == "pref_budget"][0]
    sb_use2 = [s for s in at.selectbox if s.key == "pref_use_case"][0]
    sb_ram2 = [s for s in at.selectbox if s.key == "pref_min_ram"][0]
    sb_storage2 = [s for s in at.selectbox if s.key == "pref_min_storage"][0]

    assert sb_budget2.value == "₹80,000"
    assert sb_use2.value == "Programming"
    assert sb_ram2.value == "16 GB"
    assert sb_storage2.value == "512 GB"


def test_empty_results_clears_previous_and_shows_guidance():
    """Verify restrictive search producing zero matches renders empty state and clears results."""
    at = AppTest.from_file(APP_PATH, default_timeout=15).run()

    sb_budget = [s for s in at.selectbox if s.key == "pref_budget"][0]
    sb_ram = [s for s in at.selectbox if s.key == "pref_min_ram"][0]

    # Extreme restriction: ₹30,000 budget with 32 GB RAM
    sb_budget.select("₹30,000")
    sb_ram.select("32 GB")

    at.button(key="btn_find_laptops").click().run()
    assert at.session_state["screen"] == "recommendations"

    results = at.session_state["results"]
    assert results.empty

    # Tweak filters button returns to preferences preserving selections
    btn_tweak = [b for b in at.button if b.key == "btn_tweak_empty"][0]
    btn_tweak.click().run()
    assert at.session_state["screen"] == "preferences"
    sb_ram_back = [s for s in at.selectbox if s.key == "pref_min_ram"][0]
    assert sb_ram_back.value == "32 GB"
