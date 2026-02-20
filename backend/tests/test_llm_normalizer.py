"""Tests for LLM-based ingredient normalization."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import IngredientCache
from app.services.llm_normalizer import (
    get_cached_ingredients,
    normalize_ingredients,
    normalize_with_llm,
    save_to_cache,
)


class TestNormalizeWithLLM:
    """Tests for the OpenAI normalization function."""

    @pytest.mark.asyncio
    async def test_normalize_with_llm_returns_parsed_results(self):
        """Test that LLM response is properly parsed."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "ingredients": [
                    {
                        "original": "2 cups diced tomatoes",
                        "canonical_name": "tomato",
                        "category": "Produce",
                    },
                    {
                        "original": "1 tbsp olive oil",
                        "canonical_name": "olive oil",
                        "category": "Grocery",
                    },
                ]
            }
        )

        with patch("app.services.llm_normalizer.AsyncOpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = await normalize_with_llm(["2 cups diced tomatoes", "1 tbsp olive oil"])

        assert len(result) == 2
        assert result[0]["canonical_name"] == "tomato"
        assert result[0]["category"] == "Produce"
        assert result[1]["canonical_name"] == "olive oil"

    @pytest.mark.asyncio
    async def test_normalize_with_llm_handles_array_response(self):
        """Test that direct array responses are handled."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "original": "ground cumin",
                    "canonical_name": "cumin",
                    "category": "Spices & Seasonings",
                },
            ]
        )

        with patch("app.services.llm_normalizer.AsyncOpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = await normalize_with_llm(["ground cumin"])

        assert len(result) == 1
        assert result[0]["category"] == "Spices & Seasonings"

    @pytest.mark.asyncio
    async def test_normalize_with_llm_fallback_on_parse_error(self):
        """Test graceful fallback when JSON parsing fails."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "invalid json"

        with patch("app.services.llm_normalizer.AsyncOpenAI") as mock_client_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                result = await normalize_with_llm(["some ingredient"])

        assert len(result) == 1
        assert result[0]["canonical_name"] == "some ingredient"
        assert result[0]["category"] == "Other"


class TestCaching:
    """Tests for ingredient caching functionality."""

    def test_get_cached_ingredients_returns_cached(self, test_db):
        """Test that cached ingredients are retrieved."""
        cache_entry = IngredientCache(
            original_text="2 cups flour", canonical_name="flour", category="Grocery"
        )
        test_db.add(cache_entry)
        test_db.commit()

        result = get_cached_ingredients(test_db, ["2 cups flour", "1 cup sugar"])

        assert "2 cups flour" in result
        assert result["2 cups flour"]["canonical_name"] == "flour"
        assert "1 cup sugar" not in result

    def test_save_to_cache_creates_entries(self, test_db):
        """Test that normalizations are saved to cache."""
        normalizations = [
            {"original": "diced onions", "canonical_name": "onion", "category": "Produce"},
            {"original": "minced garlic", "canonical_name": "garlic", "category": "Produce"},
        ]

        save_to_cache(test_db, normalizations)

        cached = test_db.query(IngredientCache).all()
        assert len(cached) == 2

        onion_cache = (
            test_db.query(IngredientCache)
            .filter(IngredientCache.original_text == "diced onions")
            .first()
        )
        assert onion_cache is not None
        assert onion_cache.canonical_name == "onion"

    def test_save_to_cache_skips_duplicates(self, test_db):
        """Test that duplicate entries are not created."""
        cache_entry = IngredientCache(
            original_text="2 cups flour", canonical_name="flour", category="Grocery"
        )
        test_db.add(cache_entry)
        test_db.commit()

        normalizations = [
            {"original": "2 cups flour", "canonical_name": "flour", "category": "Grocery"},
        ]

        save_to_cache(test_db, normalizations)

        cached = (
            test_db.query(IngredientCache)
            .filter(IngredientCache.original_text == "2 cups flour")
            .all()
        )
        assert len(cached) == 1


class TestNormalizeIngredients:
    """Tests for the main normalize_ingredients function."""

    @pytest.mark.asyncio
    async def test_normalize_ingredients_uses_cache(self, test_db):
        """Test that cached ingredients don't trigger LLM calls."""
        cache_entry = IngredientCache(
            original_text="2 cups flour", canonical_name="flour", category="Grocery"
        )
        test_db.add(cache_entry)
        test_db.commit()

        with patch("app.services.llm_normalizer.normalize_with_llm") as mock_llm:
            mock_llm.return_value = []

            result = await normalize_ingredients(test_db, ["2 cups flour"])

        mock_llm.assert_not_called()
        assert len(result) == 1
        assert result[0]["canonical_name"] == "flour"

    @pytest.mark.asyncio
    async def test_normalize_ingredients_calls_llm_for_uncached(self, test_db):
        """Test that uncached ingredients trigger LLM calls."""
        with patch("app.services.llm_normalizer.normalize_with_llm") as mock_llm:
            mock_llm.return_value = [
                {"original": "fresh basil", "canonical_name": "basil", "category": "Produce"}
            ]

            result = await normalize_ingredients(test_db, ["fresh basil"])

        mock_llm.assert_called_once()
        assert len(result) == 1
        assert result[0]["canonical_name"] == "basil"

    @pytest.mark.asyncio
    async def test_normalize_ingredients_mixed_cache(self, test_db):
        """Test batch with some cached and some uncached ingredients."""
        cache_entry = IngredientCache(
            original_text="2 cups flour", canonical_name="flour", category="Grocery"
        )
        test_db.add(cache_entry)
        test_db.commit()

        with patch("app.services.llm_normalizer.normalize_with_llm") as mock_llm:
            mock_llm.return_value = [
                {"original": "1 cup sugar", "canonical_name": "sugar", "category": "Grocery"}
            ]

            result = await normalize_ingredients(test_db, ["2 cups flour", "1 cup sugar"])

        mock_llm.assert_called_once_with(["1 cup sugar"])

        assert len(result) == 2
        flour = next(r for r in result if r["original"] == "2 cups flour")
        sugar = next(r for r in result if r["original"] == "1 cup sugar")
        assert flour["canonical_name"] == "flour"
        assert sugar["canonical_name"] == "sugar"

    @pytest.mark.asyncio
    async def test_normalize_ingredients_empty_list(self, test_db):
        """Test that empty list returns empty result."""
        result = await normalize_ingredients(test_db, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_normalize_ingredients_deduplicates(self, test_db):
        """Test that duplicate ingredients only trigger one LLM call."""
        with patch("app.services.llm_normalizer.normalize_with_llm") as mock_llm:
            mock_llm.return_value = [
                {"original": "salt", "canonical_name": "salt", "category": "Spices & Seasonings"}
            ]

            result = await normalize_ingredients(test_db, ["salt", "salt", "salt"])

        mock_llm.assert_called_once_with(["salt"])
        assert len(result) == 3
