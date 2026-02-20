from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with test database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_recipe_data():
    """Sample scraped recipe data for testing."""
    return {
        "url": "https://www.example.com/test-recipe",
        "title": "Test Recipe",
        "description": "A delicious test recipe",
        "image_url": "https://www.example.com/image.jpg",
        "ingredients": [
            "2 cups flour",
            "1 cup sugar",
            "3 cloves garlic",
            "1/2 teaspoon salt",
        ],
        "instructions": [
            "Mix dry ingredients",
            "Add wet ingredients",
            "Bake at 350F for 30 minutes",
        ],
        "prep_time": "15 min",
        "cook_time": "30 min",
        "total_time": "45 min",
        "servings": "4",
        "source_site": "example",
        "requires_manual_entry": False,
    }


@pytest.fixture
def saved_recipe(client, sample_recipe_data):
    """Save a recipe and return its data."""
    response = client.post("/api/recipes", json=sample_recipe_data)
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def recipe_in_box(client, saved_recipe):
    """Save a recipe and add it to the recipe box."""
    recipe_id = saved_recipe["id"]
    response = client.post(f"/api/recipes/{recipe_id}/add-to-box")
    assert response.status_code == 200
    return saved_recipe


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    fixture_path = FIXTURES_DIR / name
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    return fixture_path.read_text(encoding="utf-8")


class MockResponse:
    """Mock httpx Response object."""

    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(
                status_code=self.status_code,
                request=request,
                text=self.text,
            )
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=response,
            )


@pytest.fixture
def mock_httpx_ambitious_kitchen():
    """Mock httpx to return Ambitious Kitchen fixture."""

    async def mock_get(self, url, **kwargs):
        return MockResponse(load_fixture("ambitious_kitchen.html"))

    with patch.object(httpx.AsyncClient, "get", mock_get):
        yield


@pytest.fixture
def mock_httpx_smitten_kitchen():
    """Mock httpx to return Smitten Kitchen fixture."""

    async def mock_get(self, url, **kwargs):
        return MockResponse(load_fixture("smitten_kitchen.html"))

    with patch.object(httpx.AsyncClient, "get", mock_get):
        yield


@pytest.fixture
def mock_httpx_generic():
    """Mock httpx to return a generic page with JSON-LD."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Generic Test Recipe",
            "description": "A generic recipe for testing",
            "recipeIngredient": ["1 cup water", "2 tbsp oil"],
            "recipeInstructions": [{"@type": "HowToStep", "text": "Mix ingredients"}],
            "prepTime": "PT10M",
            "cookTime": "PT20M"
        }
        </script>
    </head>
    <body><h1>Generic Test Recipe</h1></body>
    </html>
    """

    async def mock_get(self, url, **kwargs):
        return MockResponse(html)

    with patch.object(httpx.AsyncClient, "get", mock_get):
        yield
