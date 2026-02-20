from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Recipe(Base):
    """Stored recipe with scraped data."""
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(2048), nullable=True)
    ingredients = Column(JSON, nullable=False)  # List of ingredient strings
    instructions = Column(JSON, nullable=True)  # List of instruction steps
    prep_time = Column(String(100), nullable=True)
    cook_time = Column(String(100), nullable=True)
    total_time = Column(String(100), nullable=True)
    servings = Column(String(100), nullable=True)
    source_site = Column(String(100), nullable=False)  # e.g., "nyt", "ambitiouskitchen", "smittenkitchen"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships - cascade delete to remove orphaned entries
    recipe_box_entry = relationship(
        "RecipeBoxEntry",
        back_populates="recipe",
        uselist=False,
        cascade="all, delete-orphan",
    )
    meal_plan_entries = relationship(
        "MealPlanEntry",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )


class RecipeBoxEntry(Base):
    """User's saved recipes (recipe box)."""
    __tablename__ = "recipe_box"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), unique=True, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    # Relationships
    recipe = relationship("Recipe", back_populates="recipe_box_entry")


class MealPlanEntry(Base):
    """Weekly meal plan assignments."""
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    placeholder_text = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    meal_type = Column(String(50), nullable=True)  # e.g., "breakfast", "lunch", "dinner"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe = relationship("Recipe", back_populates="meal_plan_entries")


class IngredientCache(Base):
    """Cache for LLM-normalized ingredient names and categories."""
    __tablename__ = "ingredient_cache"

    id = Column(Integer, primary_key=True, index=True)
    original_text = Column(String(500), unique=True, nullable=False, index=True)
    canonical_name = Column(String(500), nullable=False)
    category = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
