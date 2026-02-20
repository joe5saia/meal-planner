#!/usr/bin/env python3
"""Full meal planner flow test: fresh DB, save recipe, Recipe Box, Weekly Planner, Grocery List."""

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

REPORT = []


def main():
    url = "http://localhost:5173"
    recipe_url = "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def check_errors():
            # Only match error/warning banners (red background), not red UI elements like "Remove"
            err = page.locator('div.bg-red-50').first
            if err.count() > 0 and err.is_visible():
                txt = err.text_content()
                if txt and len(txt) > 3:  # Skip tiny fragments
                    return txt.strip()
            return None

        # Step 1: Navigate
        print("Step 1: Navigating to app...")
        page.goto(url, wait_until="networkidle")
        page.screenshot(path=OUTPUT_DIR / "01_nav.png", full_page=True)
        REPORT.append(("1. Navigate to app", "SUCCESS", None))

        # Step 2: Paste URL
        print("Step 2: Pasting URL...")
        page.fill('input[type="url"], input[placeholder*="URL"], input[placeholder*="Paste"]', recipe_url)
        REPORT.append(("2. Paste recipe URL", "SUCCESS", None))

        # Step 3: Click Get Recipe, wait for preview
        print("Step 3: Clicking Get Recipe...")
        page.click('button:has-text("Get Recipe")')
        try:
            page.wait_for_selector('button:has-text("Save Recipe")', state="visible", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "02_preview.png", full_page=True)
        err = check_errors()
        if page.locator('button:has-text("Save Recipe")').count() > 0:
            REPORT.append(("3. Click Get Recipe, wait for preview", "SUCCESS", err))
        else:
            REPORT.append(("3. Click Get Recipe, wait for preview", "FAILED", err))

        # Step 4: Click Save Recipe
        print("Step 4: Clicking Save Recipe...")
        page.click('button:has-text("Save Recipe")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "03_after_save.png", full_page=True)
        err = check_errors()
        if err and ("already saved" in str(err).lower() or "Recipe already" in str(err)):
            REPORT.append(("4. Click Save Recipe", "FAILED", err))
        elif err:
            REPORT.append(("4. Click Save Recipe", "FAILED", err))
        else:
            REPORT.append(("4. Click Save Recipe", "SUCCESS", None))

        # Step 5: Navigate to Recipe Box, verify recipe
        print("Step 5: Navigating to Recipe Box...")
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1500)
        page.screenshot(path=OUTPUT_DIR / "04_recipe_box.png", full_page=True)
        content = page.content()
        recipe_in_box = "Chicken Sausage" in content or "white bean" in content.lower() or "White Bean" in content
        err = check_errors()
        REPORT.append(("5. Recipe Box - chicken sausage recipe appears", "SUCCESS" if recipe_in_box else "FAILED", err))

        # Step 6: Add to Weekly Planner for Monday
        print("Step 6: Adding to Weekly Planner for Monday...")
        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "05_planner.png", full_page=True)

        # Monday is first column. Select recipe from "+ Add meal" dropdown
        first_select = page.locator('select').first
        opts = page.locator('select option')
        opt_count = opts.count()
        meal_added = False
        if first_select.count() > 0 and opt_count > 1:
            # Index 0 is "+ Add meal", index 1+ are recipes
            first_select.select_option(index=1)
            page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "06_planner_with_meal.png", full_page=True)
        planner_content = page.content()
        meal_added = "Chicken" in planner_content or "Sausage" in planner_content or "White Bean" in planner_content
        err = check_errors()
        REPORT.append(("6. Add to Weekly Planner for Monday", "SUCCESS" if meal_added else "FAILED", err or (f"Dropdown had {opt_count} options" if opt_count <= 1 else None)))

        # Step 7: Generate Grocery List and verify ingredients
        print("Step 7: Generating Grocery List...")
        gen_btn = page.locator('button:has-text("Generate Grocery List")')
        if gen_btn.count() > 0:
            if gen_btn.is_enabled():
                gen_btn.click()
                page.wait_for_timeout(4000)  # Allow API call and tab switch
            else:
                page.click('button:has-text("Grocery List")')
                page.wait_for_timeout(1000)
        page.screenshot(path=OUTPUT_DIR / "07_grocery.png", full_page=True)

        # Ensure we're on Grocery List tab
        if page.locator('button:has-text("Grocery List")').count() > 0:
            page.click('button:has-text("Grocery List")')
            page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "08_grocery_list.png", full_page=True)

        grocery_content = page.content()
        # Look for actual grocery list content (not empty state)
        empty_msg = "Select recipes from the weekly planner to generate"
        has_ingredients = (
            empty_msg not in grocery_content and
            ("olive oil" in grocery_content.lower() or
             "sausage" in grocery_content.lower() or
             "garlic" in grocery_content.lower() or
             ("From " in grocery_content and "recipe" in grocery_content.lower()))
        )
        err = check_errors()
        REPORT.append(("7. Grocery List - ingredients appear", "SUCCESS" if has_ingredients else "FAILED", err))

        browser.close()

    # Print report
    print("\n" + "=" * 70)
    print("TEST REPORT")
    print("=" * 70)
    for step, status, err in REPORT:
        err_str = f" | Error: {err}" if err else ""
        print(f"  {status:8} | {step}{err_str}")
    print("=" * 70)
    print(f"\nScreenshots: {OUTPUT_DIR}")
    return 0 if all(r[1] == "SUCCESS" for r in REPORT) else 1


if __name__ == "__main__":
    sys.exit(main())
