import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import type { Recipe } from '../api/types';
import { decodeHtmlEntities } from '../utils/text';

const INITIAL_VISIBLE_RECIPE_COUNT = 40;
const VISIBLE_RECIPE_INCREMENT = 40;

interface RecipeBoxProps {
  onSelectRecipe?: (recipe: Recipe) => void;
  onRecipeRemoved?: () => void;
  onAddToPlan?: (recipeId: number, date: string, mealType: string) => void;
  refreshTrigger?: number;
}

export function RecipeBox({ onSelectRecipe, onRecipeRemoved, onAddToPlan, refreshTrigger }: RecipeBoxProps) {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc' | 'none'>('none');
  const [addToPlanRecipe, setAddToPlanRecipe] = useState<Recipe | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [selectedMealType, setSelectedMealType] = useState<string>('dinner');
  const [visibleRecipeCount, setVisibleRecipeCount] = useState(INITIAL_VISIBLE_RECIPE_COUNT);

  const dateOptions = useMemo(() => {
    const dates: { value: string; label: string }[] = [];
    const today = new Date();
    for (let i = 0; i < 14; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      const value = date.toISOString().split('T')[0];
      const label = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      dates.push({ value, label });
    }
    return dates;
  }, []);

  useEffect(() => {
    if (addToPlanRecipe && !selectedDate) {
      setSelectedDate(dateOptions[0]?.value || '');
    }
  }, [addToPlanRecipe, selectedDate, dateOptions]);

  const handleAddToPlan = () => {
    if (addToPlanRecipe && selectedDate && onAddToPlan) {
      onAddToPlan(addToPlanRecipe.id, selectedDate, selectedMealType);
      setAddToPlanRecipe(null);
      setSelectedDate('');
      setSelectedMealType('dinner');
    }
  };

  useEffect(() => {
    setVisibleRecipeCount(INITIAL_VISIBLE_RECIPE_COUNT);
  }, [filter, sortOrder, recipes.length]);

  const fetchRecipes = async () => {
    try {
      const data = await api.recipes.getBox();
      setRecipes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recipes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecipes();
  }, [refreshTrigger]);

  const handleRemoveFromBox = async (id: number) => {
    try {
      await api.recipes.removeFromBox(id);
      setRecipes((currentRecipes) => currentRecipes.filter((recipe) => recipe.id !== id));
      onRecipeRemoved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove recipe');
    }
  };

  const normalizedFilter = filter.trim().toLowerCase();
  const filteredRecipes = useMemo(() => {
    if (!normalizedFilter) {
      return recipes;
    }

    return recipes.filter(
      (recipe) =>
        recipe.title.toLowerCase().includes(normalizedFilter) ||
        recipe.ingredients.some((ingredient) => ingredient.toLowerCase().includes(normalizedFilter))
    );
  }, [recipes, normalizedFilter]);

  const sortedRecipes = useMemo(() => {
    if (sortOrder === 'none') {
      return filteredRecipes;
    }

    const sorted = [...filteredRecipes];
    sorted.sort((a, b) => {
      if (sortOrder === 'asc') return a.title.localeCompare(b.title);
      return b.title.localeCompare(a.title);
    });
    return sorted;
  }, [filteredRecipes, sortOrder]);

  const visibleRecipes = useMemo(
    () => sortedRecipes.slice(0, visibleRecipeCount),
    [sortedRecipes, visibleRecipeCount]
  );

  if (loading) {
    return (
      <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recipe Box</h2>
        <div className="text-[#6B7B6B]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
      <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl font-semibold text-[#2D3B2D]">Recipe Box</h2>
        <span className="text-sm text-[#6B7B6B]">{recipes.length} recipes</span>
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search recipes..."
          className="w-full flex-1 rounded-lg border border-[#D8DCD0] bg-white px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-[#6B8E6B]"
        />
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc' | 'none')}
          className="w-full rounded-lg border border-[#D8DCD0] bg-white px-3 py-2 focus:border-transparent focus:ring-2 focus:ring-[#6B8E6B] sm:w-auto"
        >
          <option value="none">Sort by...</option>
          <option value="asc">Title A-Z</option>
          <option value="desc">Title Z-A</option>
        </select>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-4">{error}</div>
      )}

      {sortedRecipes.length === 0 ? (
        <div className="text-[#6B7B6B] text-center py-8">
          {filter ? 'No recipes match your search' : 'No recipes saved yet'}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {visibleRecipes.map((recipe) => (
              <div
                key={recipe.id}
                className="border border-[#D8DCD0] rounded-lg p-3 hover:border-[#6B8E6B] transition-colors bg-white"
                style={{ contentVisibility: 'auto', containIntrinsicSize: '260px' }}
              >
                <div className="flex flex-col gap-3 sm:flex-row">
                  {recipe.image_url ? (
                    <img
                      src={recipe.image_url}
                      alt={recipe.title}
                      width={320}
                      height={180}
                      loading="lazy"
                      decoding="async"
                      className="h-36 w-full rounded object-cover sm:h-20 sm:w-20"
                    />
                  ) : (
                    <div className="flex h-36 w-full items-center justify-center rounded bg-[#F0F0E8] text-[#6B7B6B] sm:h-20 sm:w-20">
                      No image
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate text-[#2D3B2D]">{decodeHtmlEntities(recipe.title)}</h3>
                    <p className="text-sm text-[#6B7B6B]">
                      {recipe.ingredients.length} ingredients
                    </p>
                    <p className="text-xs text-[#6B7B6B] mt-1">{recipe.source_site}</p>
                  </div>
                </div>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <button
                    onClick={() => onSelectRecipe?.(recipe)}
                    className="flex-1 px-3 py-1.5 border border-[#D8DCD0] rounded text-sm text-[#2D3B2D] hover:bg-[#F0F0E8] transition-colors"
                  >
                    View
                  </button>
                  <button
                    onClick={() => setAddToPlanRecipe(recipe)}
                    className="flex-1 px-3 py-1.5 bg-[#6B8E6B] text-white rounded text-sm hover:bg-[#4A6B4A] transition-colors"
                  >
                    Add to Plan
                  </button>
                </div>
                <div className="mt-2 flex justify-end">
                  <button
                    onClick={() => handleRemoveFromBox(recipe.id)}
                    className="text-xs text-red-600 hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          {visibleRecipes.length < sortedRecipes.length && (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={() => setVisibleRecipeCount((count) => count + VISIBLE_RECIPE_INCREMENT)}
                className="rounded-lg border border-[#D8DCD0] px-4 py-2 text-sm text-[#2D3B2D] hover:bg-[#F0F0E8]"
              >
                Show More Recipes ({sortedRecipes.length - visibleRecipes.length} remaining)
              </button>
            </div>
          )}
        </>
      )}

      {addToPlanRecipe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="mx-4 w-full max-w-sm rounded-lg bg-[#FAFAF7] p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-[#2D3B2D] mb-4">
              Add "{decodeHtmlEntities(addToPlanRecipe.title)}" to Plan
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#2D3B2D] mb-1">Date</label>
                <select
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-full px-3 py-2 border border-[#D8DCD0] rounded-lg focus:ring-2 focus:ring-[#6B8E6B] focus:border-transparent bg-white"
                >
                  {dateOptions.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#2D3B2D] mb-1">Meal</label>
                <select
                  value={selectedMealType}
                  onChange={(e) => setSelectedMealType(e.target.value)}
                  className="w-full px-3 py-2 border border-[#D8DCD0] rounded-lg focus:ring-2 focus:ring-[#6B8E6B] focus:border-transparent bg-white"
                >
                  <option value="breakfast">Breakfast</option>
                  <option value="lunch">Lunch</option>
                  <option value="dinner">Dinner</option>
                  <option value="dessert">Dessert</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => {
                  setAddToPlanRecipe(null);
                  setSelectedDate('');
                  setSelectedMealType('dinner');
                }}
                className="flex-1 px-4 py-2 border border-[#D8DCD0] rounded-lg text-[#2D3B2D] hover:bg-[#F0F0E8] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddToPlan}
                className="flex-1 px-4 py-2 bg-[#6B8E6B] text-white rounded-lg hover:bg-[#4A6B4A] transition-colors"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
