from datetime import date as date_type
from datetime import datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Recipe(Base):
    """Stored recipe with scraped data."""

    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    ingredients: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    instructions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    prep_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cook_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    servings: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_site: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # e.g., "nyt", "ambitiouskitchen", "smittenkitchen"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships - cascade delete to remove orphaned entries
    recipe_box_entry: Mapped[RecipeBoxEntry | None] = relationship(
        "RecipeBoxEntry",
        back_populates="recipe",
        uselist=False,
        cascade="all, delete-orphan",
    )
    meal_plan_entries: Mapped[list[MealPlanEntry]] = relationship(
        "MealPlanEntry",
        back_populates="recipe",
        cascade="all, delete-orphan",
    )


class RecipeBoxEntry(Base):
    """User's saved recipes (recipe box)."""

    __tablename__ = "recipe_box"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("recipes.id"), unique=True, nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    recipe: Mapped[Recipe] = relationship("Recipe", back_populates="recipe_box_entry")


class MealPlanEntry(Base):
    """Weekly meal plan assignments."""

    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipe_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("recipes.id"), nullable=True)
    placeholder_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    recipe: Mapped[Recipe | None] = relationship("Recipe", back_populates="meal_plan_entries")


class IngredientCache(Base):
    """Cache for LLM-normalized ingredient names and categories."""

    __tablename__ = "ingredient_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_text: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
