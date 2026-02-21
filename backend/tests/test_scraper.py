"""Tests for recipe scraping and ingredient parsing."""

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from bs4 import BeautifulSoup

from app.services.ingredient_parser import (
    aggregate_ingredients,
    is_section_header,
    normalize_ingredient_name,
    parse_ingredient,
    singularize,
)
from app.services.scraper import extract_json_ld, scrape_recipe

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class MockResponse:
    """Mock httpx Response."""

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


class TestRecipeScraping:
    """Tests for recipe scraping functionality."""

    @pytest.mark.asyncio
    async def test_scrape_ambitious_kitchen(self):
        """Test scraping an Ambitious Kitchen recipe."""
        fixture_html = load_fixture("ambitious_kitchen.html")

        async def mock_get(self, url, **kwargs):
            return MockResponse(fixture_html)

        with patch.object(httpx.AsyncClient, "get", mock_get):
            result = await scrape_recipe(
                "https://www.ambitiouskitchen.com/chicken-sausage-white-bean-bake/"
            )

        assert result["title"] == "One Pan White Wine Chicken Sausage White Bean Bake"
        assert result["source_site"] == "ambitiouskitchen"
        assert len(result["ingredients"]) == 19
        assert "2 tablespoons olive oil" in result["ingredients"]
        assert "4 cloves garlic, minced" in result["ingredients"]
        assert result["prep_time"] == "15 min"
        assert result["cook_time"] == "35 min"
        assert result["servings"] == "6 servings"
        assert result["requires_manual_entry"] is False

    @pytest.mark.asyncio
    async def test_scrape_smitten_kitchen(self):
        """Test scraping a Smitten Kitchen recipe."""
        fixture_html = load_fixture("smitten_kitchen.html")

        async def mock_get(self, url, **kwargs):
            return MockResponse(fixture_html)

        with patch.object(httpx.AsyncClient, "get", mock_get):
            result = await scrape_recipe("https://smittenkitchen.com/crispy-smashed-potatoes/")

        assert result["title"] == "Crispy Smashed Potatoes"
        assert result["source_site"] == "smittenkitchen"
        assert len(result["ingredients"]) == 11
        assert "2 pounds small yellow or red potatoes" in result["ingredients"]
        assert result["prep_time"] == "10 min"
        assert result["cook_time"] == "45 min"
        assert result["requires_manual_entry"] is False

    @pytest.mark.asyncio
    async def test_scrape_smitten_kitchen_jetpack_microdata(self):
        """Test scraping legacy Smitten Kitchen Jetpack microdata recipe markup."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="og:image" content="https://example.com/pancakes.jpg">
            <meta property="og:description" content="Fluffy buttermilk pancakes.">
        </head>
        <body>
            <div class="hrecipe h-recipe jetpack-recipe" itemscope itemtype="http://schema.org/Recipe">
                <h3 class="p-name jetpack-recipe-title fn" itemprop="name">Tall Fluffy Buttermilk Pancakes</h3>
                <ul class="jetpack-recipe-meta">
                    <li itemprop="recipeYield">Servings: Makes 14 small pancakes</li>
                    <li><time datetime="P0DT0H15M0S" itemprop="totalTime">Time: 15 minutes</time></li>
                </ul>
                <div class="jetpack-recipe-content">
                    <div class="jetpack-recipe-ingredients">
                        <ul>
                            <li itemprop="recipeIngredient">2 tablespoons butter</li>
                            <li itemprop="recipeIngredient">1 cup flour</li>
                        </ul>
                    </div>
                    <div class="jetpack-recipe-directions e-instructions">
                        <p>Whisk wet ingredients.</p>
                        <p>Fold in dry ingredients and cook.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        async def mock_get(self, url, **kwargs):
            return MockResponse(html)

        with patch.object(httpx.AsyncClient, "get", mock_get):
            result = await scrape_recipe(
                "https://smittenkitchen.com/2017/05/tall-fluffy-buttermilk-pancakes/"
            )

        assert result["title"] == "Tall Fluffy Buttermilk Pancakes"
        assert result["description"] == "Fluffy buttermilk pancakes."
        assert result["image_url"] == "https://example.com/pancakes.jpg"
        assert result["source_site"] == "smittenkitchen"
        assert result["ingredients"] == ["2 tablespoons butter", "1 cup flour"]
        assert result["instructions"] == [
            "Whisk wet ingredients.",
            "Fold in dry ingredients and cook.",
        ]
        assert result["total_time"] == "15 min"
        assert result["servings"] == "Servings: Makes 14 small pancakes"
        assert result["requires_manual_entry"] is False

    @pytest.mark.asyncio
    async def test_scrape_nyt_returns_not_supported(self):
        """Test that NYT Cooking URLs return requires_manual_entry."""
        result = await scrape_recipe("https://cooking.nytimes.com/recipes/12345-test-recipe")

        assert result["requires_manual_entry"] is True
        assert result["source_site"] == "nyt"
        assert "not currently supported" in result["error_message"].lower()
        assert result["ingredients"] == []

    @pytest.mark.asyncio
    async def test_scrape_generic_site_with_json_ld(self):
        """Test scraping a generic site with JSON-LD recipe data."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Recipe",
                "name": "Generic Test Recipe",
                "description": "A test recipe",
                "recipeIngredient": ["1 cup water", "2 tbsp oil", "salt to taste"],
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
            result = await scrape_recipe("https://www.example.com/recipe")

        assert result["title"] == "Generic Test Recipe"
        assert result["source_site"] == "unknown"
        assert len(result["ingredients"]) == 3
        assert result["prep_time"] == "10 min"
        assert result["cook_time"] == "20 min"

    @pytest.mark.asyncio
    async def test_scrape_fallback_without_json_ld(self):
        """Test fallback parsing when no JSON-LD is present."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta property="og:title" content="Simple Recipe">
            <meta property="og:description" content="A simple recipe without structured data">
            <meta property="og:image" content="https://example.com/image.jpg">
        </head>
        <body><h1>Simple Recipe</h1></body>
        </html>
        """

        async def mock_get(self, url, **kwargs):
            return MockResponse(html)

        with patch.object(httpx.AsyncClient, "get", mock_get):
            result = await scrape_recipe("https://www.example.com/simple-recipe")

        assert result["title"] == "Simple Recipe"
        assert result["requires_manual_entry"] is True
        assert result["ingredients"] == []


class TestJsonLdExtraction:
    """Tests for JSON-LD extraction."""

    def test_extract_json_ld_simple(self):
        """Test extracting a simple JSON-LD recipe."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {"@type": "Recipe", "name": "Test Recipe", "recipeIngredient": ["flour", "sugar"]}
            </script>
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")
        result = extract_json_ld(soup)

        assert result is not None
        assert result["name"] == "Test Recipe"
        assert result["recipeIngredient"] == ["flour", "sugar"]

    def test_extract_json_ld_from_graph(self):
        """Test extracting recipe from @graph structure."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "WebPage", "name": "Page"},
                    {"@type": "Recipe", "name": "Graph Recipe", "recipeIngredient": ["eggs"]}
                ]
            }
            </script>
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "lxml")
        result = extract_json_ld(soup)

        assert result is not None
        assert result["name"] == "Graph Recipe"

    def test_extract_json_ld_returns_none_when_missing(self):
        """Test that None is returned when no JSON-LD is present."""
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        result = extract_json_ld(soup)

        assert result is None


class TestIngredientParser:
    """Tests for ingredient parsing."""

    def test_parse_simple_ingredient(self):
        """Test parsing a simple ingredient string."""
        result = parse_ingredient("2 cups flour")

        assert result["quantity"] == 2.0
        assert result["unit"] == "cup"
        assert result["name"] == "flour"

    def test_parse_ingredient_with_tablespoon(self):
        """Test parsing with tablespoon abbreviation."""
        result = parse_ingredient("3 tbsp olive oil")

        assert result["quantity"] == 3.0
        assert result["unit"] == "tablespoon"
        assert result["name"] == "olive oil"

    def test_parse_ingredient_with_fraction(self):
        """Test parsing with unicode fraction."""
        result = parse_ingredient("½ teaspoon salt")

        assert result["quantity"] == 0.5
        assert result["unit"] == "teaspoon"
        assert result["name"] == "salt"

    def test_parse_ingredient_with_range(self):
        """Test parsing ingredient with quantity range (takes average)."""
        result = parse_ingredient("2-3 cloves garlic")

        assert result["quantity"] == 2.5  # Average of 2 and 3
        assert result["unit"] == "clove"
        assert result["name"] == "garlic"

    def test_parse_ingredient_no_quantity(self):
        """Test parsing ingredient without quantity."""
        result = parse_ingredient("salt to taste")

        assert result["quantity"] is None
        assert result["name"] == "salt to taste"

    def test_parse_ingredient_with_parenthetical(self):
        """Test that parenthetical notes are removed."""
        result = parse_ingredient("1 cup chicken broth (or vegetable broth)")

        assert result["quantity"] == 1.0
        assert result["unit"] == "cup"
        assert "broth" in result["name"].lower()


class TestIngredientAggregation:
    """Tests for ingredient aggregation."""

    def test_aggregate_same_ingredients(self):
        """Test combining identical ingredients."""
        ingredients = [
            "2 cloves garlic",
            "3 cloves garlic",
        ]

        result = aggregate_ingredients(ingredients)

        garlic = next(item for item in result if "garlic" in item["name"].lower())
        assert garlic["quantity"] == "5"
        assert garlic["unit"] == "clove"
        assert len(garlic["original_strings"]) == 2

    def test_aggregate_different_ingredients(self):
        """Test that different ingredients stay separate."""
        ingredients = [
            "1 cup flour",
            "2 cups sugar",
        ]

        result = aggregate_ingredients(ingredients)

        assert len(result) == 2
        flour = next(item for item in result if "flour" in item["name"].lower())
        sugar = next(item for item in result if "sugar" in item["name"].lower())
        assert flour["quantity"] == "1"
        assert sugar["quantity"] == "2"

    def test_aggregate_preserves_original_strings(self):
        """Test that original strings are preserved."""
        ingredients = [
            "2 tablespoons olive oil",
            "1 tablespoon olive oil, for drizzling",
        ]

        result = aggregate_ingredients(ingredients)

        oil = next(item for item in result if "olive oil" in item["name"].lower())
        assert len(oil["original_strings"]) == 2
        assert "2 tablespoons olive oil" in oil["original_strings"]

    def test_aggregate_sorts_alphabetically(self):
        """Test that results are sorted alphabetically."""
        ingredients = [
            "1 cup zucchini",
            "2 cups apple",
            "1 cup banana",
        ]

        result = aggregate_ingredients(ingredients)
        names = [item["name"].lower() for item in result]

        assert names == sorted(names)


class TestNormalizeIngredientName:
    """Tests for ingredient name normalization."""

    def test_normalize_removes_adjectives(self):
        """Test that common adjectives are removed."""
        assert "garlic" in normalize_ingredient_name("fresh garlic")
        assert "parsley" in normalize_ingredient_name("chopped parsley")
        assert "tomato" in normalize_ingredient_name("diced tomatoes")

    def test_normalize_lowercases(self):
        """Test that names are lowercased."""
        assert normalize_ingredient_name("FLOUR") == "flour"
        assert normalize_ingredient_name("Brown Sugar") == "brown sugar"

    def test_normalize_singularizes(self):
        """Test that plurals are normalized to singular."""
        assert normalize_ingredient_name("tomatoes") == "tomato"
        assert normalize_ingredient_name("onions") == "onion"
        assert normalize_ingredient_name("berries") == "berry"

    def test_normalize_sorts_words(self):
        """Test that word order is normalized (sorted)."""
        assert normalize_ingredient_name("garlic clove") == normalize_ingredient_name(
            "clove garlic"
        )

    def test_normalize_descriptors_and_plurals(self):
        """Test combined descriptor removal and plural normalization."""
        assert normalize_ingredient_name("diced green onions") == normalize_ingredient_name(
            "chopped green onion"
        )


class TestSectionHeaderDetection:
    """Tests for section header detection."""

    def test_for_the_header(self):
        """Test 'For the...' patterns are detected."""
        assert is_section_header("For the sauce:")
        assert is_section_header("For the filling:")
        assert is_section_header("For the crust")
        assert is_section_header("For serving:")

    def test_colon_ending_header(self):
        """Test headers ending with colon are detected."""
        assert is_section_header("Sauce:")
        assert is_section_header("Toppings:")
        assert is_section_header("Garnish:")

    def test_single_word_headers(self):
        """Test single-word section names are detected."""
        assert is_section_header("sauce")
        assert is_section_header("filling")
        assert is_section_header("marinade")
        assert is_section_header("dressing")

    def test_real_ingredients_not_flagged(self):
        """Test that real ingredients are not flagged as headers."""
        assert not is_section_header("2 cups flour")
        assert not is_section_header("1 tablespoon olive oil")
        assert not is_section_header("4 cloves garlic, minced")
        assert not is_section_header("salt and pepper to taste")

    def test_empty_string_is_header(self):
        """Test that empty strings are treated as headers."""
        assert is_section_header("")
        assert is_section_header("   ")


class TestSingularize:
    """Tests for the singularize function."""

    def test_regular_plurals(self):
        """Test regular -s plurals."""
        assert singularize("onions") == "onion"
        assert singularize("carrots") == "carrot"
        assert singularize("cloves") == "clove"

    def test_es_plurals(self):
        """Test -es plurals."""
        assert singularize("tomatoes") == "tomato"
        assert singularize("potatoes") == "potato"
        assert singularize("dishes") == "dish"

    def test_ies_plurals(self):
        """Test -ies plurals."""
        assert singularize("berries") == "berry"
        assert singularize("cherries") == "cherry"

    def test_already_singular(self):
        """Test words already singular."""
        assert singularize("garlic") == "garlic"
        assert singularize("flour") == "flour"

    def test_words_ending_in_ss(self):
        """Test words ending in 'ss' are not changed."""
        assert singularize("grass") == "grass"
        assert singularize("bass") == "bass"


class TestAggregationWithImprovedMatching:
    """Tests for ingredient aggregation with improved name matching."""

    def test_aggregate_word_order_variations(self):
        """Test that 'garlic clove' and 'clove garlic' are combined."""
        ingredients = [
            "2 cloves garlic",
            "1 clove garlic",
        ]

        result = aggregate_ingredients(ingredients)
        garlic_items = [item for item in result if "garlic" in item["name"].lower()]

        assert len(garlic_items) == 1
        assert garlic_items[0]["quantity"] == "3"

    def test_aggregate_plural_variations(self):
        """Test that 'onion' and 'onions' are combined."""
        ingredients = [
            "1 cup diced onion",
            "1 cup chopped onions",
        ]

        result = aggregate_ingredients(ingredients)
        onion_items = [item for item in result if "onion" in item["name"].lower()]

        assert len(onion_items) == 1
        assert onion_items[0]["quantity"] == "2"

    def test_aggregate_descriptor_variations(self):
        """Test that different descriptors for same ingredient combine."""
        ingredients = [
            "1 cup diced tomatoes",
            "1 cup chopped tomatoes",
        ]

        result = aggregate_ingredients(ingredients)
        tomato_items = [item for item in result if "tomato" in item["name"].lower()]

        assert len(tomato_items) == 1
        assert tomato_items[0]["quantity"] == "2"

    def test_aggregate_filters_section_headers(self):
        """Test that section headers are filtered out during aggregation."""
        ingredients = [
            "For the sauce:",
            "1 cup tomato sauce",
            "2 cloves garlic",
            "For the filling:",
            "1 cup ricotta cheese",
        ]

        result = aggregate_ingredients(ingredients)

        names = [item["name"].lower() for item in result]
        assert not any("for the" in name for name in names)
        assert not any(name.endswith(":") for name in names)
        assert len(result) == 3


class TestUnitExtractionFromAnywhere:
    """Tests for extracting units from any position in ingredient string."""

    def test_unit_at_beginning(self):
        """Test unit extraction when unit is first word after quantity."""
        result = parse_ingredient("2 cloves garlic")

        assert result["quantity"] == 2.0
        assert result["unit"] == "clove"
        assert result["name"] == "garlic"

    def test_unit_at_end(self):
        """Test unit extraction when unit is last word."""
        result = parse_ingredient("1 garlic clove")

        assert result["quantity"] == 1.0
        assert result["unit"] == "clove"
        assert result["name"] == "garlic"

    def test_unit_in_middle(self):
        """Test unit extraction when unit is in the middle."""
        result = parse_ingredient("2 minced cloves garlic")

        assert result["quantity"] == 2.0
        assert result["unit"] == "clove"
        assert "garlic" in result["name"]

    def test_garlic_clove_aggregation(self):
        """Test that 'garlic clove' and 'clove garlic' aggregate together."""
        ingredients = [
            "2 cloves garlic",
            "1 garlic clove",
        ]

        result = aggregate_ingredients(ingredients)
        garlic_items = [item for item in result if "garlic" in item["name"].lower()]

        assert len(garlic_items) == 1
        assert garlic_items[0]["quantity"] == "3"
        assert garlic_items[0]["unit"] == "clove"

    def test_multiple_unit_candidates(self):
        """Test that only first matching unit is extracted."""
        result = parse_ingredient("1 can diced tomatoes")

        assert result["unit"] == "can"
        assert "tomatoes" in result["name"]

    def test_bunch_extraction(self):
        """Test bunch unit extraction from different positions."""
        result1 = parse_ingredient("1 bunch green onions")
        result2 = parse_ingredient("1 green onion bunch")

        assert result1["unit"] == "bunch"
        assert result2["unit"] == "bunch"
        assert "green" in result1["name"] or "onion" in result1["name"]
