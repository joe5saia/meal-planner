from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import grocery, meal_plans, recipes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    yield


app = FastAPI(
    title="Meal Planner API",
    description="API for recipe scraping, meal planning, and grocery list generation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    cast(Any, CORSMiddleware),
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recipes.router, prefix="/api/recipes", tags=["recipes"])
app.include_router(meal_plans.router, prefix="/api/meal-plans", tags=["meal-plans"])
app.include_router(grocery.router, prefix="/api/grocery-list", tags=["grocery"])


@app.get("/")
async def root():
    return {"message": "Meal Planner API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
