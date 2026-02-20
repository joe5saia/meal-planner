#!/usr/bin/env python3
"""Test grocery list consistency fix: remove from Recipe Box should clear grocery list."""

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
    # Smitten Kitchen crispy smashed potatoes URL (2023/03) returns 404; use Ambitious Kitchen
    recipe_url = "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/"

    report = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        # Phase 1: Add recipe
        print("Phase 1: Adding Crispy Smashed Potatoes recipe...")
        if page.locator('button:has-text("Add Recipe")').count() > 0:
            page.click('button:has-text("Add Recipe")')
        page.wait_for_timeout(500)
        page.fill('input[type="url"], input[placeholder*="Paste"]', recipe_url)
        page.click('button:has-text("Get Recipe")')
        try:
            page.wait_for_selector('button:has-text("Save Recipe")', timeout=25000)
        except Exception:
            page.screenshot(path=OUTPUT_DIR / "fix_00_scrape_failed.png", full_page=True)
            print("  Scrape may have failed - check screenshot")
        page.wait_for_timeout(2000)
        save_btn = page.locator('button:has-text("Save Recipe")')
        if save_btn.count() > 0:
            save_btn.click()
            page.wait_for_timeout(2000)
        else:
            print("  Save Recipe button not found")
        page.screenshot(path=OUTPUT_DIR / "fix_01_after_save.png", full_page=True)

        err = page.locator('div.bg-red-50').first.text_content() if page.locator('div.bg-red-50').count() > 0 else None
        report.append(("1. Add recipe (Save)", "FAILED" if err else "SUCCESS", err))

        # Phase 2: Verify in Recipe Box, add to planner, generate grocery list
        print("Phase 2: Recipe Box -> Planner -> Generate Grocery List...")
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1500)
        page.screenshot(path=OUTPUT_DIR / "fix_02_recipe_box.png", full_page=True)

        content = page.content()
        recipe_in_box = "chicken" in content.lower() or "sausage" in content.lower() or "bean" in content.lower()
        report.append(("2. Recipe in Recipe Box", "SUCCESS" if recipe_in_box else "FAILED", None))

        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)

        # Add to Tuesday (index 2) - first select has Monday, second has Tuesday
        selects = page.locator('select')
        if selects.count() >= 2:
            selects.nth(1).select_option(index=1)  # Tuesday, first recipe
        else:
            selects.first.select_option(index=1)
        page.wait_for_timeout(1500)

        gen_btn = page.locator('button:has-text("Generate Grocery List")')
        if gen_btn.is_enabled():
            gen_btn.click()
            page.wait_for_timeout(4000)

        grocery_content = page.content()
        had_ingredients = "olive oil" in grocery_content.lower() or "sausage" in grocery_content.lower() or "From 1 recipe" in grocery_content
        report.append(("3. Grocery List has ingredients", "SUCCESS" if had_ingredients else "FAILED", None))
        page.screenshot(path=OUTPUT_DIR / "fix_03_grocery_before_remove.png", full_page=True)

        # Phase 3: Remove from Recipe Box
        print("Phase 3: Removing from Recipe Box...")
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1500)
        page.locator('button:has-text("Remove")').first.click()
        page.wait_for_timeout(2000)

        # Phase 4: Check Grocery List - should be empty with fix
        print("Phase 4: Checking Grocery List after remove...")
        page.click('button:has-text("Grocery List")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "fix_04_grocery_after_remove.png", full_page=True)

        grocery_after = page.content()
        empty_msg = "Select recipes from the weekly planner" in grocery_after
        still_has_ingredients = "olive oil" in grocery_after.lower() or "sausage" in grocery_after.lower() or "From 1 recipe" in grocery_after
        grocery_cleared = empty_msg or not still_has_ingredients
        report.append(("4. Grocery List empty after remove (FIX)", "SUCCESS" if grocery_cleared else "FAILED", None))

        # Phase 5: Check Weekly Planner
        print("Phase 5: Checking Weekly Planner...")
        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "fix_05_planner_after_remove.png", full_page=True)

        btn_text = page.locator('button:has-text("Generate Grocery List")').text_content() or ""
        planner_empty = "(0 meals)" in btn_text
        report.append(("5. Weekly Planner empty after remove", "SUCCESS" if planner_empty else "FAILED", None))

        browser.close()

    print("\n" + "=" * 70)
    print("GROCERY LIST CONSISTENCY FIX - TEST REPORT")
    print("=" * 70)
    for step, status, err in report:
        err_str = f" | {err}" if err else ""
        print(f"  {status:8} | {step}{err_str}")
    print("=" * 70)

    grocery_ok = next((r[1] == "SUCCESS" for r in report if "4. Grocery" in r[0]), False)
    planner_ok = next((r[1] == "SUCCESS" for r in report if "5. Weekly" in r[0]), False)

    print("\nANSWERS:")
    print(f"  Did removing from Recipe Box clear the grocery list? {'YES' if grocery_ok else 'NO'}")
    print(f"  Is the Weekly Planner also empty after removal? {'YES' if planner_ok else 'NO'}")
    print("\nScreenshots:", OUTPUT_DIR)

    return 0 if grocery_ok and planner_ok else 1


if __name__ == "__main__":
    sys.exit(main())
