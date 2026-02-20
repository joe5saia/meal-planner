"""
Consistency tests for recipe deletion cascade and cross-tab sync.

These tests verify that:
1. Deleting a recipe cascades to RecipeBoxEntry
2. Deleting a recipe cascades to MealPlanEntry
3. Removing from recipe box removes associated meal plan entries
"""

from datetime import date, timedelta


class TestRecipeDeletionConsistency:
    """Tests for recipe deletion cascade behavior."""

    def test_delete_recipe_removes_from_box(self, client, recipe_in_box):
        """Deleting a recipe should remove it from the recipe box."""
        recipe_id = recipe_in_box["id"]

        box_response = client.get("/api/recipes/box/all")
        assert any(r["id"] == recipe_id for r in box_response.json())

        client.delete(f"/api/recipes/{recipe_id}")

        box_response = client.get("/api/recipes/box/all")
        box_ids = [r["id"] for r in box_response.json()]

        assert recipe_id not in box_ids, "Recipe should not appear in box after deletion"

    def test_delete_recipe_removes_from_meal_plans(self, client, recipe_in_box):
        """Deleting a recipe should remove it from all meal plans."""
        recipe_id = recipe_in_box["id"]

        date1 = date.today().isoformat()
        date2 = (date.today() + timedelta(days=2)).isoformat()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": date1})
        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": date2})

        plans_before = client.get("/api/meal-plans").json()
        assert len([mp for mp in plans_before if mp["recipe_id"] == recipe_id]) == 2

        client.delete(f"/api/recipes/{recipe_id}")

        plans_after = client.get("/api/meal-plans").json()
        recipe_plans = [mp for mp in plans_after if mp["recipe_id"] == recipe_id]

        assert len(recipe_plans) == 0, "All meal plan entries for the recipe should be deleted"


class TestRecipeBoxMealPlanConsistency:
    """Tests for consistency between recipe box and meal plans."""

    def test_remove_from_box_removes_from_meal_plans(self, client, recipe_in_box):
        """Removing a recipe from the box should remove it from meal plans."""
        recipe_id = recipe_in_box["id"]
        plan_date = (date.today() + timedelta(days=1)).isoformat()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date})

        plans_before = client.get("/api/meal-plans").json()
        assert any(mp["recipe_id"] == recipe_id for mp in plans_before)

        client.delete(f"/api/recipes/{recipe_id}/remove-from-box")

        plans_after = client.get("/api/meal-plans").json()
        recipe_plans = [mp for mp in plans_after if mp["recipe_id"] == recipe_id]

        assert len(recipe_plans) == 0, (
            "Meal plan entries should be removed when recipe is removed from box"
        )

    def test_remove_from_box_deletes_recipe(self, client, recipe_in_box, test_db):
        """Verify that removing from recipe box deletes the recipe from database."""
        from app.models import Recipe

        recipe_id = recipe_in_box["id"]

        assert test_db.query(Recipe).filter(Recipe.id == recipe_id).first() is not None

        client.delete(f"/api/recipes/{recipe_id}/remove-from-box")

        test_db.expire_all()
        assert test_db.query(Recipe).filter(Recipe.id == recipe_id).first() is None


class TestGroceryListConsistency:
    """Tests for grocery list consistency with meal plans."""

    def test_delete_recipe_updates_grocery_list(self, client, recipe_in_box):
        """Deleting a recipe should update the grocery list."""
        recipe_id = recipe_in_box["id"]
        plan_date = (date.today() + timedelta(days=3)).isoformat()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date})

        grocery_before = client.post(
            "/api/grocery-list", json={"start_date": plan_date, "end_date": plan_date}
        ).json()
        assert len(grocery_before["items"]) > 0, "Should have grocery items from meal plan"

        client.delete(f"/api/recipes/{recipe_id}")

        grocery_after = client.post(
            "/api/grocery-list", json={"start_date": plan_date, "end_date": plan_date}
        ).json()

        assert len(grocery_after["items"]) == 0, (
            "Grocery list should be empty after deleting the only recipe"
        )


class TestOrphanedDataDetection:
    """Tests to detect orphaned database records."""

    def test_no_orphaned_box_entries(self, client, sample_recipe_data, test_db):
        """Detect orphaned recipe box entries after recipe deletion."""
        from app.models import RecipeBoxEntry

        save_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = save_response.json()["id"]
        client.post(f"/api/recipes/{recipe_id}/add-to-box")

        box_entries_before = (
            test_db.query(RecipeBoxEntry).filter(RecipeBoxEntry.recipe_id == recipe_id).count()
        )
        assert box_entries_before == 1

        client.delete(f"/api/recipes/{recipe_id}")

        orphaned = (
            test_db.query(RecipeBoxEntry).filter(RecipeBoxEntry.recipe_id == recipe_id).count()
        )

        assert orphaned == 0, f"Found {orphaned} orphaned RecipeBoxEntry records"

    def test_no_orphaned_meal_plan_entries(self, client, sample_recipe_data, test_db):
        """Detect orphaned meal plan entries after recipe deletion."""
        from app.models import MealPlanEntry

        save_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = save_response.json()["id"]
        client.post(f"/api/recipes/{recipe_id}/add-to-box")

        plan_date = (date.today() + timedelta(days=4)).isoformat()
        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date})

        entries_before = (
            test_db.query(MealPlanEntry).filter(MealPlanEntry.recipe_id == recipe_id).count()
        )
        assert entries_before == 1

        client.delete(f"/api/recipes/{recipe_id}")

        orphaned = test_db.query(MealPlanEntry).filter(MealPlanEntry.recipe_id == recipe_id).count()

        assert orphaned == 0, f"Found {orphaned} orphaned MealPlanEntry records"
