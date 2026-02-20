"""E2E test fixtures for Playwright tests."""
import pytest
import subprocess
import time
import os
import signal
from pathlib import Path


BASE_URL = "http://localhost:5173"
API_URL = "http://localhost:8000"

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def ensure_servers_running():
    """
    Check that both frontend and backend servers are running.
    
    This fixture does NOT start the servers automatically - they should be
    started separately using `./run.sh` before running e2e tests.
    
    To run e2e tests:
    1. In terminal 1: cd hack_day_project && ./run.sh
    2. In terminal 2: cd hack_day_project/e2e && pytest
    """
    import httpx
    
    try:
        response = httpx.get(f"{API_URL}/api/recipes", timeout=5.0)
        response.raise_for_status()
    except Exception as e:
        pytest.skip(
            f"Backend server not running at {API_URL}. "
            "Start it with ./run.sh before running e2e tests."
        )
    
    try:
        response = httpx.get(BASE_URL, timeout=5.0)
    except Exception as e:
        pytest.skip(
            f"Frontend server not running at {BASE_URL}. "
            "Start it with ./run.sh before running e2e tests."
        )


@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context for tests."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture
def page(browser, ensure_servers_running):
    """Create a new page for each test."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()
    yield page
    page.close()
    context.close()


@pytest.fixture
def clean_database():
    """
    Reset the database before tests.
    
    Note: This requires the backend to have a reset endpoint or
    you need to manually clear the database file.
    """
    import httpx
    import sqlite3
    
    db_path = PROJECT_ROOT / "backend" / "recipes.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM meal_plan_entries")
        cursor.execute("DELETE FROM recipe_box_entries")
        cursor.execute("DELETE FROM recipes")
        
        conn.commit()
        conn.close()
    
    yield


TEST_URLS = {
    "ambitious_kitchen": "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/",
    "smitten_kitchen": "https://smittenkitchen.com/crispy-smashed-potatoes/",
}
