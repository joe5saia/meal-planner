#!/usr/bin/env python3
"""Test consistency after removing recipe from Recipe Box."""

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
    report = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Step 1: Navigate to Recipe Box
        print("Step 1: Navigating to Recipe Box...")
        page.click('button:has-text("Recipe Box")')
        page.wait_for_timeout(1500)
        page.screenshot(path=OUTPUT_DIR / "remove_01_recipe_box.png", full_page=True)

        # Step 2 & 3: Find recipe and click Remove
        print("Step 2-3: Finding recipe and clicking Remove...")
        remove_btn = page.locator('button:has-text("Remove")')
        if remove_btn.count() > 0:
            remove_btn.first.click()
            page.wait_for_timeout(2000)
            report.append(("Remove from Recipe Box", "SUCCESS"))
        else:
            report.append(("Remove from Recipe Box", "FAILED - No Remove button found"))

        page.screenshot(path=OUTPUT_DIR / "remove_02_after_remove.png", full_page=True)

        # Step 4 & 5: Navigate to Weekly Planner, check if recipe still appears
        print("Step 4-5: Checking Weekly Planner...")
        page.click('button:has-text("Weekly Planner")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "remove_03_weekly_planner.png", full_page=True)

        # Check: "Generate Grocery List (0 meals)" = no meals (good); "(1 meals)" = meal still there (bad)
        meal_count_btn = page.locator('button:has-text("Generate Grocery List")')
        btn_text = meal_count_btn.text_content() if meal_count_btn.count() > 0 else ""
        planner_empty = "(0 meals)" in btn_text
        report.append(("Weekly Planner - recipe should NOT appear", "SUCCESS" if planner_empty else "FAILED - recipe still on planner"))

        # Step 6 & 7: Navigate to Grocery List, check ingredients
        print("Step 6-7: Checking Grocery List...")
        page.click('button:has-text("Grocery List")')
        page.wait_for_timeout(2000)
        page.screenshot(path=OUTPUT_DIR / "remove_04_grocery_list.png", full_page=True)

        grocery_content = page.content()
        has_ingredients = (
            "olive oil" in grocery_content.lower() or
            "sausage" in grocery_content.lower() or
            "garlic" in grocery_content.lower()
        )
        empty_state = "Select recipes from the weekly planner" in grocery_content
        report.append(("Grocery List - should be empty (0 ingredients)", 
            "SUCCESS" if (empty_state or not has_ingredients) else "FAILED - ingredients still appear"))

        browser.close()

    print("\n" + "=" * 70)
    print("CONSISTENCY REPORT: Remove from Recipe Box")
    print("=" * 70)
    for step, status in report:
        print(f"  {status:8} | {step}")
    print("=" * 70)
    print(f"\nScreenshots: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
