from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Recipe, RecipeBoxEntry, MealPlanEntry
from ..services.scraper import scrape_recipe

router = APIRouter()


class ScrapeRequest(BaseModel):
    url: HttpUrl


class RecipeResponse(BaseModel):
    id: int
    url: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: list[str]
    instructions: Optional[list[str]] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[str] = None
    source_site: str
    created_at: datetime
    in_recipe_box: bool = False

    class Config:
        from_attributes = True


class ScrapedRecipeResponse(BaseModel):
    url: str
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    ingredients: list[str]
    instructions: Optional[list[str]] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[str] = None
    source_site: str
    requires_manual_entry: bool = False
    error_message: Optional[str] = None


@router.post("/scrape", response_model=ScrapedRecipeResponse)
async def scrape_recipe_endpoint(request: ScrapeRequest):
    """Scrape a recipe from a URL and return the extracted data."""
    try:
        result = await scrape_recipe(str(request.url))
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[RecipeResponse])
async def list_recipes(db: Session = Depends(get_db)):
    """List all saved recipes."""
    recipes = db.query(Recipe).all()
    result = []
    for recipe in recipes:
        recipe_dict = {
            "id": recipe.id,
            "url": recipe.url,
            "title": recipe.title,
            "description": recipe.description,
            "image_url": recipe.image_url,
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions,
            "prep_time": recipe.prep_time,
            "cook_time": recipe.cook_time,
            "total_time": recipe.total_time,
            "servings": recipe.servings,
            "source_site": recipe.source_site,
            "created_at": recipe.created_at,
            "in_recipe_box": recipe.recipe_box_entry is not None,
        }
        result.append(RecipeResponse(**recipe_dict))
    return result


@router.get("/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a specific recipe by ID."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RecipeResponse(
        id=recipe.id,
        url=recipe.url,
        title=recipe.title,
        description=recipe.description,
        image_url=recipe.image_url,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        prep_time=recipe.prep_time,
        cook_time=recipe.cook_time,
        total_time=recipe.total_time,
        servings=recipe.servings,
        source_site=recipe.source_site,
        created_at=recipe.created_at,
        in_recipe_box=recipe.recipe_box_entry is not None,
    )


@router.post("", response_model=RecipeResponse)
async def save_recipe(recipe_data: ScrapedRecipeResponse, db: Session = Depends(get_db)):
    """Save a scraped recipe to the database."""
    existing = db.query(Recipe).filter(Recipe.url == recipe_data.url).first()
    if existing:
        raise HTTPException(status_code=400, detail="Recipe already saved")
    
    recipe = Recipe(
        url=recipe_data.url,
        title=recipe_data.title,
        description=recipe_data.description,
        image_url=recipe_data.image_url,
        ingredients=recipe_data.ingredients,
        instructions=recipe_data.instructions,
        prep_time=recipe_data.prep_time,
        cook_time=recipe_data.cook_time,
        total_time=recipe_data.total_time,
        servings=recipe_data.servings,
        source_site=recipe_data.source_site,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    
    return RecipeResponse(
        id=recipe.id,
        url=recipe.url,
        title=recipe.title,
        description=recipe.description,
        image_url=recipe.image_url,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        prep_time=recipe.prep_time,
        cook_time=recipe.cook_time,
        total_time=recipe.total_time,
        servings=recipe.servings,
        source_site=recipe.source_site,
        created_at=recipe.created_at,
        in_recipe_box=False,
    )


@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Delete a recipe."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    db.delete(recipe)
    db.commit()
    return {"message": "Recipe deleted"}


# Recipe Box endpoints
@router.post("/{recipe_id}/add-to-box")
async def add_to_recipe_box(recipe_id: int, db: Session = Depends(get_db)):
    """Add a recipe to the recipe box."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    existing = db.query(RecipeBoxEntry).filter(RecipeBoxEntry.recipe_id == recipe_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Recipe already in recipe box")
    
    entry = RecipeBoxEntry(recipe_id=recipe_id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "recipe_id": recipe_id, "message": "Added to recipe box"}


@router.delete("/{recipe_id}/remove-from-box")
async def remove_from_recipe_box(recipe_id: int, db: Session = Depends(get_db)):
    """Remove a recipe from the recipe box and delete it from the database."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    db.delete(recipe)
    db.commit()
    return {"message": "Recipe deleted"}


@router.get("/box/all", response_model=list[RecipeResponse])
async def get_recipe_box(db: Session = Depends(get_db)):
    """Get all recipes in the recipe box."""
    entries = db.query(RecipeBoxEntry).all()
    result = []
    for entry in entries:
        recipe = entry.recipe
        result.append(RecipeResponse(
            id=recipe.id,
            url=recipe.url,
            title=recipe.title,
            description=recipe.description,
            image_url=recipe.image_url,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            total_time=recipe.total_time,
            servings=recipe.servings,
            source_site=recipe.source_site,
            created_at=recipe.created_at,
            in_recipe_box=True,
        ))
    return result
