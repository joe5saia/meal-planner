"""API integration tests for recipes, meal plans, and grocery endpoints."""

from datetime import date, timedelta


class TestRecipeEndpoints:
    """Tests for /api/recipes endpoints."""

    def test_create_recipe(self, client, sample_recipe_data):
        """Test creating a new recipe."""
        response = client.post("/api/recipes", json=sample_recipe_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_recipe_data["title"]
        assert data["url"] == sample_recipe_data["url"]
        assert data["id"] is not None

    def test_get_recipe(self, client, saved_recipe):
        """Test retrieving a recipe by ID."""
        recipe_id = saved_recipe["id"]
        response = client.get(f"/api/recipes/{recipe_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recipe_id
        assert data["title"] == saved_recipe["title"]

    def test_get_nonexistent_recipe(self, client):
        """Test retrieving a recipe that doesn't exist."""
        response = client.get("/api/recipes/99999")

        assert response.status_code == 404

    def test_list_recipes(self, client, saved_recipe):
        """Test listing all recipes."""
        response = client.get("/api/recipes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(r["id"] == saved_recipe["id"] for r in data)

    def test_delete_recipe(self, client, saved_recipe):
        """Test deleting a recipe."""
        recipe_id = saved_recipe["id"]

        response = client.delete(f"/api/recipes/{recipe_id}")
        assert response.status_code == 200

        response = client.get(f"/api/recipes/{recipe_id}")
        assert response.status_code == 404


class TestRecipeBoxEndpoints:
    """Tests for recipe box functionality."""

    def test_add_to_recipe_box(self, client, saved_recipe):
        """Test adding a recipe to the recipe box."""
        recipe_id = saved_recipe["id"]

        response = client.post(f"/api/recipes/{recipe_id}/add-to-box")

        assert response.status_code == 200
        data = response.json()
        assert data["recipe_id"] == recipe_id

    def test_add_to_box_duplicate(self, client, recipe_in_box):
        """Test that adding a recipe twice returns error."""
        recipe_id = recipe_in_box["id"]

        response = client.post(f"/api/recipes/{recipe_id}/add-to-box")
        assert response.status_code == 400

    def test_get_recipe_box(self, client, recipe_in_box):
        """Test retrieving all recipes in the box."""
        response = client.get("/api/recipes/box/all")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(r["id"] == recipe_in_box["id"] for r in data)

    def test_remove_from_recipe_box(self, client, recipe_in_box):
        """Test removing a recipe from the box."""
        recipe_id = recipe_in_box["id"]

        response = client.delete(f"/api/recipes/{recipe_id}/remove-from-box")
        assert response.status_code == 200

        response = client.get("/api/recipes/box/all")
        data = response.json()
        assert not any(r["id"] == recipe_id for r in data)


class TestMealPlanEndpoints:
    """Tests for /api/meal-plans endpoints."""

    def test_add_to_meal_plan(self, client, recipe_in_box):
        """Test adding a recipe to a day's meal plan."""
        recipe_id = recipe_in_box["id"]
        plan_date = date.today().isoformat()

        response = client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date})

        assert response.status_code == 200
        data = response.json()
        assert data["recipe_id"] == recipe_id
        assert data["date"] == plan_date

    def test_get_meal_plans(self, client, recipe_in_box):
        """Test retrieving all meal plans."""
        recipe_id = recipe_in_box["id"]
        plan_date = (date.today() + timedelta(days=1)).isoformat()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date})

        response = client.get("/api/meal-plans")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_meal_plans_by_date_range(self, client, recipe_in_box):
        """Test retrieving meal plans for a specific date range."""
        recipe_id = recipe_in_box["id"]
        plan_date = date.today()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date.isoformat()})

        response = client.get(
            f"/api/meal-plans?start_date={plan_date.isoformat()}&end_date={plan_date.isoformat()}"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(mp["date"] == plan_date.isoformat() for mp in data)

    def test_delete_meal_plan(self, client, recipe_in_box):
        """Test removing a recipe from a meal plan."""
        recipe_id = recipe_in_box["id"]
        plan_date = (date.today() + timedelta(days=2)).isoformat()

        add_response = client.post(
            "/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date}
        )
        meal_plan_id = add_response.json()["id"]

        response = client.delete(f"/api/meal-plans/{meal_plan_id}")
        assert response.status_code == 200

        response = client.get("/api/meal-plans")
        data = response.json()
        assert not any(mp["id"] == meal_plan_id for mp in data)


class TestGroceryEndpoints:
    """Tests for /api/grocery endpoints."""

    def test_get_grocery_list_by_recipe_ids(self, client, saved_recipe):
        """Test grocery list generation by recipe IDs."""
        recipe_id = saved_recipe["id"]

        response = client.post("/api/grocery-list", json={"recipe_ids": [recipe_id]})

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["recipe_count"] == 1
        assert len(data["items"]) > 0

    def test_get_grocery_list_by_date_range(self, client, recipe_in_box):
        """Test grocery list generation by date range."""
        recipe_id = recipe_in_box["id"]
        plan_date = date.today()

        client.post("/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date.isoformat()})

        response = client.post(
            "/api/grocery-list",
            json={"start_date": plan_date.isoformat(), "end_date": plan_date.isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["recipe_count"] >= 1

    def test_get_grocery_list_aggregates_ingredients(self, client, sample_recipe_data):
        """Test that grocery list aggregates ingredients from multiple recipes."""
        response1 = client.post("/api/recipes", json=sample_recipe_data)
        recipe1_id = response1.json()["id"]

        recipe2_data = sample_recipe_data.copy()
        recipe2_data["url"] = "https://www.example.com/test-recipe-2"
        recipe2_data["title"] = "Test Recipe 2"
        response2 = client.post("/api/recipes", json=recipe2_data)
        recipe2_id = response2.json()["id"]

        response = client.post("/api/grocery-list", json={"recipe_ids": [recipe1_id, recipe2_id]})

        assert response.status_code == 200
        data = response.json()
        assert data["recipe_count"] == 2

        flour_item = next((item for item in data["items"] if "flour" in item["name"].lower()), None)
        assert flour_item is not None
        assert flour_item["quantity"] == "4"


class TestRecipeUIReflection:
    """Tests that verify UI actions are reflected in the database."""

    def test_save_and_add_to_box_workflow(self, client, sample_recipe_data):
        """Test the full workflow of saving and adding to box."""
        save_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = save_response.json()["id"]

        box_response = client.post(f"/api/recipes/{recipe_id}/add-to-box")
        assert box_response.status_code == 200

        list_response = client.get("/api/recipes/box/all")
        box_recipes = list_response.json()
        assert any(r["id"] == recipe_id for r in box_recipes)

    def test_add_to_meal_plan_workflow(self, client, sample_recipe_data):
        """Test full workflow from save to meal plan."""
        save_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = save_response.json()["id"]

        client.post(f"/api/recipes/{recipe_id}/add-to-box")

        plan_date = date.today().isoformat()
        plan_response = client.post(
            "/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date}
        )
        assert plan_response.status_code == 200

        list_response = client.get(f"/api/meal-plans?start_date={plan_date}&end_date={plan_date}")
        plans = list_response.json()
        assert any(mp["recipe_id"] == recipe_id for mp in plans)

    def test_grocery_list_updates_with_meal_plan_changes(self, client, sample_recipe_data):
        """Test that grocery list reflects meal plan changes."""
        save_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = save_response.json()["id"]
        client.post(f"/api/recipes/{recipe_id}/add-to-box")

        plan_date = (date.today() + timedelta(days=5)).isoformat()
        add_response = client.post(
            "/api/meal-plans", json={"recipe_id": recipe_id, "date": plan_date}
        )
        meal_plan_id = add_response.json()["id"]

        grocery_response = client.post(
            "/api/grocery-list", json={"start_date": plan_date, "end_date": plan_date}
        )
        initial_count = grocery_response.json()["recipe_count"]
        assert initial_count == 1

        client.delete(f"/api/meal-plans/{meal_plan_id}")

        grocery_response = client.post(
            "/api/grocery-list", json={"start_date": plan_date, "end_date": plan_date}
        )
        final_count = grocery_response.json()["recipe_count"]
        assert final_count == 0
