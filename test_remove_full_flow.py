#!/usr/bin/env python3
"""
Full consistency test: Add recipe -> Add to planner -> Generate grocery list
-> Remove from Recipe Box -> Verify planner and grocery list update.
"""

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent / "test_screenshots"
OUTPUT_DIR.mkdir(exist_ok=True)


def main():
    url = "http://localhost:5173"
    recipe_url = "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        # Phase 1: Add recipe, add to planner, generate grocery list
        page.fill('input[type="url"], input[placeholder*="Paste"]', recipe_url)
        page.click('button:has-text("Get Recipe")')
        page.wait_for_selector('button:has-text("Save Recipe")', timeout=15000)
        page.wait_for_timeout(2000)
        page.click('button:has-text("Save Recipe")')
        page.wait_for_timeout(2000)

        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)
        page.locator('select').first.select_option(index=1)
        page.wait_for_timeout(1500)

        gen_btn = page.locator('button:has-text("Generate Grocery List")')
        gen_btn.click()
        page.wait_for_timeout(4000)

        # Verify we have grocery list with ingredients
        grocery_before = page.content()
        had_ingredients_before = "olive oil" in grocery_before.lower() or "sausage" in grocery_before.lower()
        print(f"Phase 1 complete. Grocery list had ingredients: {had_ingredients_before}")

        # Phase 2: Remove from Recipe Box
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1500)
        page.locator('button:has-text("Remove")').first.click()
        page.wait_for_timeout(2000)

        # Phase 3: Check Weekly Planner
        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)
        btn_text = page.locator('button:has-text("Generate Grocery List")').text_content() or ""
        planner_empty = "(0 meals)" in btn_text
        print(f"Phase 3. Weekly Planner after remove: {'0 meals (correct)' if planner_empty else 'still has meals'}")

        # Phase 4: Check Grocery List - does it still show ingredients?
        page.click('button:has-text("Grocery List")')
        page.wait_for_timeout(2000)
        grocery_after = page.content()
        has_ingredients_after = "olive oil" in grocery_after.lower() or "sausage" in grocery_after.lower()
        empty_msg = "Select recipes from the weekly planner" in grocery_after
        print(f"Phase 4. Grocery List: ingredients={'yes' if has_ingredients_after else 'no'}, empty_state={empty_msg}")

        page.screenshot(path=OUTPUT_DIR / "consistency_grocery_after_remove.png", full_page=True)
        browser.close()

    print("\n" + "=" * 70)
    print("CONSISTENCY SUMMARY")
    print("=" * 70)
    print("After removing from Recipe Box:")
    print(f"  - Weekly Planner: recipe {'GONE' if planner_empty else 'STILL THERE'} (expected: GONE)")
    print(f"  - Grocery List:   {'EMPTY (0 ingredients)' if (empty_msg or not has_ingredients_after) else 'STILL HAS INGREDIENTS'} (expected: empty)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
