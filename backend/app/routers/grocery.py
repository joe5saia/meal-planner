import os
import re
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date

from ..database import get_db
from ..models import MealPlanEntry, Recipe
from ..services.ingredient_parser import parse_ingredient, is_section_header
from ..services.llm_normalizer import normalize_ingredients

router = APIRouter()

GROCERY_SECTIONS = {
    'Produce': [
        'onion', 'garlic', 'tomato', 'pepper', 'carrot', 'celery', 'lettuce',
        'spinach', 'kale', 'broccoli', 'cauliflower', 'potato', 'zucchini',
        'squash', 'cucumber', 'mushroom', 'parsley', 'cilantro', 'basil',
        'thyme', 'rosemary', 'lemon', 'lime', 'apple', 'banana', 'berry',
        'avocado', 'ginger', 'scallion', 'shallot', 'leek', 'cabbage',
        'corn', 'asparagus', 'green bean', 'pea', 'radish', 'beet', 'turnip',
        'jalapen', 'chili', 'serrano', 'habanero', 'arugula', 'chard',
        'fennel', 'artichoke', 'eggplant', 'okra', 'sweet potato', 'yam'
    ],
    'Meat & Seafood': [
        'chicken', 'beef', 'pork', 'sausage', 'bacon', 'turkey', 'lamb',
        'fish', 'salmon', 'shrimp', 'tuna', 'steak', 'roast',
        'ham', 'prosciutto', 'anchov', 'crab', 'lobster', 'scallop',
        'mussels', 'clam', 'cod', 'tilapia', 'halibut', 'mahi'
    ],
    'Dairy': [
        'milk', 'cheese', 'butter', 'cream', 'yogurt', 'egg', 'sour cream',
        'parmesan', 'mozzarella', 'cheddar', 'feta', 'ricotta', 'goat cheese',
        'cream cheese', 'half and half', 'whipping cream', 'mascarpone',
        'brie', 'gruyere', 'swiss', 'provolone', 'cottage cheese'
    ],
    'Bakery & Deli': [
        'bread', 'roll', 'tortilla', 'pita', 'bun', 'croissant', 'bagel',
        'english muffin', 'naan', 'flatbread', 'deli', 'ciabatta', 'baguette'
    ],
    'Frozen': [
        'frozen'
    ],
    'Grocery': [
        'flour', 'sugar', 'oil', 'vinegar', 'honey', 'maple',
        'rice', 'pasta', 'noodle', 'oat', 'breadcrumb', 'cornstarch',
        'baking', 'vanilla', 'soy sauce', 'worcestershire', 'broth',
        'stock', 'coconut milk', 'olive oil', 'vegetable oil', 'canola',
        'quinoa', 'couscous', 'barley', 'farro', 'lentil', 'grain'
    ],
    'Canned & Jarred': [
        'canned', 'can of', 'beans', 'tomato paste', 'tomato sauce',
        'diced tomato', 'crushed tomato', 'chickpea', 'black bean',
        'kidney bean', 'white bean', 'pinto bean', 'jar', 'pickle'
    ],
    'Spices & Seasonings': [
        'cumin', 'paprika', 'oregano', 'cinnamon', 'nutmeg', 'cayenne',
        'chili powder', 'curry', 'turmeric', 'coriander', 'pepper flake',
        'bay leaf', 'allspice', 'cardamom', 'fennel seed', 'salt',
        'mustard seed', 'black pepper', 'white pepper', 'seasoning',
        'sage', 'dill', 'tarragon', 'marjoram', 'ground cumin',
        'ground cinnamon', 'ground nutmeg', 'kosher salt', 'sea salt',
        'red pepper', 'crushed red'
    ],
}

SECTION_ORDER = [
    'Produce', 'Meat & Seafood', 'Dairy', 'Bakery & Deli',
    'Frozen', 'Grocery', 'Canned & Jarred', 'Spices & Seasonings', 'Other'
]


def get_category(ingredient_name: str) -> str:
    """Categorize an ingredient using keyword matching."""
    lower = ingredient_name.lower()
    
    if re.search(r'\b(canned|diced tomato|crushed tomato|tomato sauce|tomato paste)\b', lower):
        return 'Canned & Jarred'
    if 'frozen' in lower:
        return 'Frozen'
    
    if re.search(r'\bground\s+(cumin|cinnamon|nutmeg|ginger|clove|allspice|cardamom|coriander|turmeric|pepper)\b', lower):
        return 'Spices & Seasonings'
    if re.search(r'\bground\s+(beef|turkey|pork|chicken|lamb|meat)\b', lower):
        return 'Meat & Seafood'
    
    for section in SECTION_ORDER[:-1]:
        keywords = GROCERY_SECTIONS.get(section, [])
        if any(kw in lower for kw in keywords):
            return section
    
    return 'Other'


class GroceryListRequest(BaseModel):
    recipe_ids: Optional[list[int]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class GroceryItem(BaseModel):
    name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None
    category: str = "Other"
    original_strings: list[str]


class GroceryListResponse(BaseModel):
    items: list[GroceryItem]
    recipe_count: int
    recipe_titles: list[str]


async def aggregate_with_llm(db: Session, ingredients: list[str]) -> list[dict]:
    """Aggregate ingredients using LLM-based normalization."""
    filtered = [ing for ing in ingredients if not is_section_header(ing)]
    
    if not filtered:
        return []
    
    parsed_ingredients = [parse_ingredient(ing) for ing in filtered]
    
    normalizations = await normalize_ingredients(db, filtered)
    
    norm_map = {n["original"]: n for n in normalizations}
    
    grouped = defaultdict(list)
    for i, parsed in enumerate(parsed_ingredients):
        original = filtered[i]
        norm = norm_map.get(original, {"canonical_name": parsed["name"], "category": "Other"})
        key = (norm["canonical_name"], parsed["unit"], norm["category"])
        grouped[key].append({
            "parsed": parsed,
            "original": original,
            "category": norm["category"]
        })
    
    result = []
    for (canonical_name, unit, category), items in grouped.items():
        original_strings = [item["original"] for item in items]
        
        quantities = [item["parsed"]["quantity"] for item in items if item["parsed"]["quantity"] is not None]
        
        if quantities:
            total_qty = sum(quantities)
            if total_qty == int(total_qty):
                quantity_str = str(int(total_qty))
            else:
                quantity_str = f"{total_qty:.2f}".rstrip("0").rstrip(".")
        else:
            quantity_str = None
        
        result.append({
            "name": canonical_name,
            "quantity": quantity_str,
            "unit": unit,
            "category": category,
            "original_strings": original_strings,
        })
    
    result.sort(key=lambda x: x["name"].lower())
    
    return result


def aggregate_without_llm(ingredients: list[str]) -> list[dict]:
    """Fallback aggregation using rule-based normalization."""
    from ..services.ingredient_parser import aggregate_ingredients
    items = aggregate_ingredients(ingredients)
    for item in items:
        item["category"] = get_category(item["name"])
    return items


@router.post("", response_model=GroceryListResponse)
async def generate_grocery_list(
    request: GroceryListRequest,
    db: Session = Depends(get_db)
):
    """Generate an aggregated grocery list from recipes or meal plan dates."""
    recipes = []
    
    if request.recipe_ids:
        recipes = db.query(Recipe).filter(Recipe.id.in_(request.recipe_ids)).all()
    elif request.start_date and request.end_date:
        entries = db.query(MealPlanEntry).filter(
            MealPlanEntry.date >= request.start_date,
            MealPlanEntry.date <= request.end_date
        ).all()
        recipes = [entry.recipe for entry in entries]
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either recipe_ids or both start_date and end_date"
        )
    
    if not recipes:
        return GroceryListResponse(items=[], recipe_count=0, recipe_titles=[])
    
    all_ingredients = []
    for recipe in recipes:
        all_ingredients.extend(recipe.ingredients)
    
    use_llm = os.getenv("OPENAI_API_KEY") is not None
    
    if use_llm:
        try:
            aggregated = await aggregate_with_llm(db, all_ingredients)
        except Exception:
            aggregated = aggregate_without_llm(all_ingredients)
    else:
        aggregated = aggregate_without_llm(all_ingredients)
    
    return GroceryListResponse(
        items=aggregated,
        recipe_count=len(recipes),
        recipe_titles=[r.title for r in recipes],
    )
