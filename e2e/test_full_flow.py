"""
End-to-end tests for the meal planning application.

These tests require both frontend and backend servers to be running.
Start with: ./run.sh

Then run tests with: cd e2e && pytest
"""
import pytest
from playwright.sync_api import Page, expect
import time


BASE_URL = "http://localhost:5173"


class TestRecipeSearchAndSave:
    """Tests for recipe search and save functionality."""

    def test_search_page_loads(self, page: Page):
        """Test that the search page loads correctly."""
        page.goto(BASE_URL)
        
        expect(page.locator("h1")).to_contain_text("Meal Planner")
        expect(page.get_by_role("textbox")).to_be_visible()
        expect(page.get_by_role("button", name="Search")).to_be_visible()

    def test_tab_navigation(self, page: Page):
        """Test navigation between tabs."""
        page.goto(BASE_URL)
        
        page.click("text=Recipe Box")
        expect(page.locator("main")).to_contain_text("Recipe Box")
        
        page.click("text=Weekly Planner")
        expect(page.locator("main")).to_contain_text("Weekly")
        
        page.click("text=Grocery List")
        expect(page.locator("main")).to_contain_text("Grocery")
        
        page.click("text=Search")
        expect(page.get_by_role("textbox")).to_be_visible()

    @pytest.mark.skip(reason="Requires live scraping - run manually when needed")
    def test_scrape_and_save_recipe(self, page: Page, clean_database):
        """Test scraping a recipe and saving it to the box."""
        page.goto(BASE_URL)
        
        url_input = page.get_by_role("textbox")
        url_input.fill("https://smittenkitchen.com/2023/03/crispy-smashed-potatoes/")
        
        page.click("text=Search")
        
        page.wait_for_selector("text=Save Recipe", timeout=30000)
        
        expect(page.locator(".recipe-preview")).to_contain_text("Crispy")
        
        page.click("text=Save Recipe")
        
        page.wait_for_timeout(1000)
        
        page.click("text=Recipe Box")
        page.wait_for_timeout(500)
        
        expect(page.locator("main")).to_contain_text("Crispy")


class TestRecipeBox:
    """Tests for recipe box management."""

    def test_empty_recipe_box(self, page: Page, clean_database):
        """Test that empty recipe box shows appropriate message."""
        page.goto(BASE_URL)
        page.click("text=Recipe Box")
        
        expect(page.locator("main")).to_contain_text("No recipes")

    def test_remove_recipe_from_box(self, page: Page):
        """Test removing a recipe from the box."""
        page.goto(BASE_URL)
        page.click("text=Recipe Box")
        
        recipe_cards = page.locator("[data-testid='recipe-card']")
        if recipe_cards.count() == 0:
            pytest.skip("No recipes in box to remove")
        
        initial_count = recipe_cards.count()
        
        page.locator("[data-testid='remove-from-box']").first.click()
        
        page.wait_for_timeout(500)
        
        assert page.locator("[data-testid='recipe-card']").count() < initial_count


class TestWeeklyPlanner:
    """Tests for weekly meal planning."""

    def test_planner_shows_days(self, page: Page):
        """Test that all days of the week are shown."""
        page.goto(BASE_URL)
        page.click("text=Weekly Planner")
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for day in days:
            expect(page.locator("main")).to_contain_text(day)

    def test_add_recipe_to_day(self, page: Page):
        """Test adding a recipe to a specific day."""
        page.goto(BASE_URL)
        
        page.click("text=Recipe Box")
        recipe_cards = page.locator("[data-testid='recipe-card']")
        
        if recipe_cards.count() == 0:
            pytest.skip("No recipes in box to add to planner")
        
        first_recipe = recipe_cards.first
        recipe_name = first_recipe.locator("h3").text_content()
        
        first_recipe.locator("button", has_text="Add to").click()
        page.locator("text=Monday").click()
        
        page.click("text=Weekly Planner")
        page.wait_for_timeout(500)
        
        monday_section = page.locator("[data-day='monday']")
        expect(monday_section).to_contain_text(recipe_name)


class TestGroceryList:
    """Tests for grocery list generation."""

    def test_empty_grocery_list(self, page: Page, clean_database):
        """Test that empty grocery list shows appropriate message."""
        page.goto(BASE_URL)
        page.click("text=Grocery List")
        
        expect(page.locator("main")).to_contain_text("No ingredients")

    def test_grocery_list_aggregation(self, page: Page):
        """Test that grocery list aggregates ingredients from meal plan."""
        page.goto(BASE_URL)
        page.click("text=Grocery List")
        
        items = page.locator("[data-testid='grocery-item']")
        
        if items.count() == 0:
            pytest.skip("No grocery items (no recipes in meal plan)")
        
        for i in range(min(3, items.count())):
            item = items.nth(i)
            expect(item.locator(".quantity")).to_be_visible()
            expect(item.locator(".ingredient-name")).to_be_visible()


class TestCrossTabConsistency:
    """Tests for consistency across different tabs."""

    @pytest.mark.skip(reason="Known bug - cascade delete not implemented")
    def test_delete_from_box_removes_from_planner(self, page: Page):
        """
        KNOWN BUG: Removing a recipe from the box should remove it from the planner.
        
        This test is skipped until the consistency bug is fixed.
        """
        page.goto(BASE_URL)
        page.click("text=Recipe Box")
        
        recipe_cards = page.locator("[data-testid='recipe-card']")
        if recipe_cards.count() == 0:
            pytest.skip("No recipes in box")
        
        first_recipe = recipe_cards.first
        recipe_name = first_recipe.locator("h3").text_content()
        
        first_recipe.locator("button", has_text="Add to").click()
        page.locator("text=Tuesday").click()
        
        page.click("text=Weekly Planner")
        expect(page.locator("main")).to_contain_text(recipe_name)
        
        page.click("text=Recipe Box")
        page.locator("[data-testid='remove-from-box']").first.click()
        page.wait_for_timeout(500)
        
        page.click("text=Weekly Planner")
        page.wait_for_timeout(500)
        
        expect(page.locator("main")).not_to_contain_text(recipe_name)

    def test_planner_reflects_box_additions(self, page: Page):
        """Test that recipes added to box are available in planner."""
        page.goto(BASE_URL)
        page.click("text=Recipe Box")
        
        recipe_cards = page.locator("[data-testid='recipe-card']")
        if recipe_cards.count() == 0:
            pytest.skip("No recipes in box")
        
        recipe_names = []
        for i in range(min(3, recipe_cards.count())):
            name = recipe_cards.nth(i).locator("h3").text_content()
            recipe_names.append(name)
        
        page.click("text=Weekly Planner")
        
        add_button = page.locator("[data-testid='add-recipe-dropdown']").first
        add_button.click()
        
        dropdown = page.locator("[data-testid='recipe-dropdown']")
        
        for name in recipe_names:
            expect(dropdown).to_contain_text(name)
