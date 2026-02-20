#!/usr/bin/env python3
"""Test the meal planner app: scrape recipe, save, and verify it appears in Recipe Box."""

import sys
from pathlib import Path

# Add parent for potential playwright install
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "test_screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    url = "http://localhost:5173"
    recipe_url = "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/"

    observations = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Step 1: Navigate to app
        print("Step 1: Navigating to", url)
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=OUTPUT_DIR / "01_initial_page.png", full_page=True)
        observations.append("Step 1: Loaded initial page - Meal Planner with Add Recipe, Recipe Box, Weekly Planner, Grocery List tabs")
        print("  Screenshot: 01_initial_page.png")

        # Step 2: Already have screenshot from step 1 (initial page)

        # Step 3: Paste URL into input field
        print("Step 3: Pasting recipe URL into input...")
        input_selector = 'input[type="url"], input[placeholder*="URL"], input[placeholder*="Paste"]'
        page.fill(input_selector, recipe_url)
        observations.append("Step 3: Pasted recipe URL into input field")
        page.screenshot(path=OUTPUT_DIR / "02_url_entered.png", full_page=True)
        print("  Screenshot: 02_url_entered.png")

        # Step 4: Click Get Recipe
        print("Step 4: Clicking Get Recipe...")
        page.click('button:has-text("Get Recipe")')
        observations.append("Step 4: Clicked Get Recipe button")

        # Step 5: Wait for recipe to load
        print("Step 5: Waiting for recipe to load...")
        try:
            page.wait_for_selector('img[alt]', state="visible", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "03_recipe_preview.png", full_page=True)
        if page.locator('button:has-text("Save Recipe")').count() > 0:
            observations.append("Step 5: Recipe loaded successfully - preview with title, image, ingredients visible")
        else:
            observations.append("Step 5: Recipe may have failed to load or still loading - check screenshot")
        print("  Screenshot: 03_recipe_preview.png")

        # Step 6: Click Save Recipe
        print("Step 6: Clicking Save Recipe...")
        save_btn = page.locator('button:has-text("Save Recipe")')
        if save_btn.count() > 0:
            save_btn.click()
            page.wait_for_timeout(1500)
            observations.append("Step 6: Clicked Save Recipe button")
        else:
            observations.append("Step 6: Save Recipe button not found - recipe may not have loaded")

        # Step 7: Screenshot after save
        page.screenshot(path=OUTPUT_DIR / "04_after_save.png", full_page=True)
        if page.locator('div.bg-red-50, [class*="error"]').count() > 0:
            observations.append("Step 7: Error message may be shown after save")
        else:
            observations.append("Step 7: Save completed - form likely cleared, URL input empty")
        print("  Screenshot: 04_after_save.png")

        # Step 8: Click Recipe Box tab
        print("Step 8: Clicking Recipe Box tab...")
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1000)

        # Step 9: Screenshot Recipe Box
        page.screenshot(path=OUTPUT_DIR / "05_recipe_box.png", full_page=True)
        print("  Screenshot: 05_recipe_box.png")

        # Check if recipe appears
        content = page.content()
        if "Chicken Sausage" in content or "white bean" in content.lower() or "White Bean" in content:
            observations.append("Step 9: Recipe APPEARS in Recipe Box!")
        else:
            observations.append("Step 9: Recipe DOES NOT appear in Recipe Box - saved recipes may need to be added to box separately")
        print("  Checking Recipe Box content...")

        browser.close()

    print("\n" + "=" * 60)
    print("OBSERVATIONS")
    print("=" * 60)
    for obs in observations:
        print("•", obs)
    print("\nScreenshots saved to:", OUTPUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
