from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import date, datetime

from ..database import get_db
from ..models import MealPlanEntry, Recipe

router = APIRouter()


class MealPlanCreate(BaseModel):
    recipe_id: Optional[int] = None
    placeholder_text: Optional[str] = None
    date: date
    meal_type: Optional[str] = None

    @model_validator(mode='after')
    def validate_recipe_or_placeholder(self):
        if self.recipe_id is None and not self.placeholder_text:
            raise ValueError('Either recipe_id or placeholder_text must be provided')
        if self.recipe_id is not None and self.placeholder_text:
            raise ValueError('Cannot provide both recipe_id and placeholder_text')
        return self


class MealPlanUpdate(BaseModel):
    meal_type: Optional[str] = None


class MealPlanResponse(BaseModel):
    id: int
    recipe_id: Optional[int] = None
    recipe_title: Optional[str] = None
    recipe_image_url: Optional[str] = None
    placeholder_text: Optional[str] = None
    date: date
    meal_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[MealPlanResponse])
async def get_meal_plans(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get meal plans, optionally filtered by date range."""
    query = db.query(MealPlanEntry)
    
    if start_date:
        query = query.filter(MealPlanEntry.date >= start_date)
    if end_date:
        query = query.filter(MealPlanEntry.date <= end_date)
    
    entries = query.order_by(MealPlanEntry.date).all()
    
    result = []
    for entry in entries:
        if entry.recipe_id and entry.recipe:
            result.append(MealPlanResponse(
                id=entry.id,
                recipe_id=entry.recipe_id,
                recipe_title=entry.recipe.title,
                recipe_image_url=entry.recipe.image_url,
                placeholder_text=None,
                date=entry.date,
                meal_type=entry.meal_type,
                created_at=entry.created_at,
            ))
        else:
            result.append(MealPlanResponse(
                id=entry.id,
                recipe_id=None,
                recipe_title=None,
                recipe_image_url=None,
                placeholder_text=entry.placeholder_text,
                date=entry.date,
                meal_type=entry.meal_type,
                created_at=entry.created_at,
            ))
    return result


@router.post("", response_model=MealPlanResponse)
async def create_meal_plan(plan: MealPlanCreate, db: Session = Depends(get_db)):
    """Assign a recipe or placeholder to a specific date."""
    recipe = None
    if plan.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == plan.recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
    
    entry = MealPlanEntry(
        recipe_id=plan.recipe_id,
        placeholder_text=plan.placeholder_text,
        date=plan.date,
        meal_type=plan.meal_type,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    
    return MealPlanResponse(
        id=entry.id,
        recipe_id=entry.recipe_id,
        recipe_title=recipe.title if recipe else None,
        recipe_image_url=recipe.image_url if recipe else None,
        placeholder_text=entry.placeholder_text,
        date=entry.date,
        meal_type=entry.meal_type,
        created_at=entry.created_at,
    )


@router.put("/{plan_id}", response_model=MealPlanResponse)
async def update_meal_plan(
    plan_id: int,
    plan: MealPlanCreate,
    db: Session = Depends(get_db)
):
    """Update a meal plan entry."""
    entry = db.query(MealPlanEntry).filter(MealPlanEntry.id == plan_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    
    recipe = None
    if plan.recipe_id:
        recipe = db.query(Recipe).filter(Recipe.id == plan.recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")
    
    entry.recipe_id = plan.recipe_id
    entry.placeholder_text = plan.placeholder_text
    entry.date = plan.date
    entry.meal_type = plan.meal_type
    
    db.commit()
    db.refresh(entry)
    
    return MealPlanResponse(
        id=entry.id,
        recipe_id=entry.recipe_id,
        recipe_title=recipe.title if recipe else None,
        recipe_image_url=recipe.image_url if recipe else None,
        placeholder_text=entry.placeholder_text,
        date=entry.date,
        meal_type=entry.meal_type,
        created_at=entry.created_at,
    )


@router.patch("/{plan_id}", response_model=MealPlanResponse)
async def patch_meal_plan(
    plan_id: int,
    update: MealPlanUpdate,
    db: Session = Depends(get_db)
):
    """Partially update a meal plan entry (e.g., change meal type)."""
    entry = db.query(MealPlanEntry).filter(MealPlanEntry.id == plan_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    
    if update.meal_type is not None:
        entry.meal_type = update.meal_type
    
    db.commit()
    db.refresh(entry)
    
    recipe = entry.recipe if entry.recipe_id else None
    
    return MealPlanResponse(
        id=entry.id,
        recipe_id=entry.recipe_id,
        recipe_title=recipe.title if recipe else None,
        recipe_image_url=recipe.image_url if recipe else None,
        placeholder_text=entry.placeholder_text,
        date=entry.date,
        meal_type=entry.meal_type,
        created_at=entry.created_at,
    )


@router.delete("/{plan_id}")
async def delete_meal_plan(plan_id: int, db: Session = Depends(get_db)):
    """Delete a meal plan entry."""
    entry = db.query(MealPlanEntry).filter(MealPlanEntry.id == plan_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    
    db.delete(entry)
    db.commit()
    return {"message": "Meal plan deleted"}
