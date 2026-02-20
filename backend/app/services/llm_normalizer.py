"""LLM-based ingredient normalization with caching."""
import os
import json
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from ..models import IngredientCache


SYSTEM_PROMPT = """You are an ingredient normalizer for a grocery list app. Given a list of raw ingredient strings, return a JSON array where each element has:
- "original": the original ingredient string (exactly as provided)
- "canonical_name": simplified, singular form of the ingredient name only (no quantities, units, or prep methods)
- "category": one of these exact values: "Produce", "Meat & Seafood", "Dairy", "Bakery & Deli", "Frozen", "Grocery", "Canned & Jarred", "Spices & Seasonings", "Other"

Rules:
1. Strip ALL preparation methods: diced, chopped, minced, sliced, freshly ground, finely chopped, etc.
2. Strip ALL quantities and units: 2 cups, 1 tablespoon, 3 cloves, etc.
3. Use singular forms: "tomato" not "tomatoes", "onion" not "onions"
4. For compound items like "salt and pepper", split into separate entries
5. Ground SPICES go to "Spices & Seasonings" (e.g., ground cumin, ground cinnamon)
6. Ground MEAT goes to "Meat & Seafood" (e.g., ground beef, ground turkey)
7. Fresh herbs (basil, cilantro, parsley, thyme, rosemary) go to "Produce"
8. Dried spices and seasonings go to "Spices & Seasonings"
9. Canned/jarred items go to "Canned & Jarred"
10. Normalize similar items to the same canonical name:
    - "green onion", "scallion", "spring onion" -> "green onion"
    - "bell pepper", "red bell pepper", "green bell pepper" -> "bell pepper" (but preserve color if specified)

Return ONLY valid JSON array, no markdown or explanation."""


async def normalize_with_llm(ingredients: list[str]) -> list[dict]:
    """Call OpenAI to normalize a batch of ingredients."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = AsyncOpenAI(api_key=api_key)
    
    user_message = "Normalize these ingredients:\n" + "\n".join(f"- {ing}" for ing in ingredients)
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
        if isinstance(result, dict) and "ingredients" in result:
            return result["ingredients"]
        elif isinstance(result, list):
            return result
        else:
            return list(result.values())[0] if result else []
    except json.JSONDecodeError:
        return [{"original": ing, "canonical_name": ing.lower(), "category": "Other"} for ing in ingredients]


def get_cached_ingredients(db: Session, ingredients: list[str]) -> dict[str, dict]:
    """Look up cached normalizations for ingredients."""
    cached = {}
    if not ingredients:
        return cached
    
    cache_entries = db.query(IngredientCache).filter(
        IngredientCache.original_text.in_(ingredients)
    ).all()
    
    for entry in cache_entries:
        cached[entry.original_text] = {
            "canonical_name": entry.canonical_name,
            "category": entry.category
        }
    
    return cached


def save_to_cache(db: Session, normalizations: list[dict]) -> None:
    """Save LLM normalizations to cache."""
    for item in normalizations:
        original = item.get("original", "")
        if not original:
            continue
        
        existing = db.query(IngredientCache).filter(
            IngredientCache.original_text == original
        ).first()
        
        if not existing:
            cache_entry = IngredientCache(
                original_text=original,
                canonical_name=item.get("canonical_name", original.lower()),
                category=item.get("category", "Other")
            )
            db.add(cache_entry)
    
    db.commit()


async def normalize_ingredients(
    db: Session,
    ingredients: list[str]
) -> list[dict]:
    """
    Normalize ingredients using cache and LLM.
    
    Returns list of dicts with:
    - original: original ingredient string
    - canonical_name: normalized name
    - category: grocery store section
    """
    if not ingredients:
        return []
    
    unique_ingredients = list(set(ingredients))
    
    cached = get_cached_ingredients(db, unique_ingredients)
    
    uncached = [ing for ing in unique_ingredients if ing not in cached]
    
    if uncached:
        llm_results = await normalize_with_llm(uncached)
        save_to_cache(db, llm_results)
        
        for item in llm_results:
            original = item.get("original", "")
            if original:
                cached[original] = {
                    "canonical_name": item.get("canonical_name", original.lower()),
                    "category": item.get("category", "Other")
                }
    
    results = []
    for ing in ingredients:
        if ing in cached:
            results.append({
                "original": ing,
                "canonical_name": cached[ing]["canonical_name"],
                "category": cached[ing]["category"]
            })
        else:
            results.append({
                "original": ing,
                "canonical_name": ing.lower(),
                "category": "Other"
            })
    
    return results
