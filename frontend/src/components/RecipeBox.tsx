import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import type { Recipe } from '../api/types';
import { decodeHtmlEntities } from '../utils/text';

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
      setRecipes(recipes.filter((r) => r.id !== id));
      onRecipeRemoved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove recipe');
    }
  };

  const filteredRecipes = recipes.filter(
    (r) =>
      r.title.toLowerCase().includes(filter.toLowerCase()) ||
      r.ingredients.some((i) => i.toLowerCase().includes(filter.toLowerCase()))
  );

  const sortedRecipes = [...filteredRecipes].sort((a, b) => {
    if (sortOrder === 'asc') return a.title.localeCompare(b.title);
    if (sortOrder === 'desc') return b.title.localeCompare(a.title);
    return 0;
  });

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
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-[#2D3B2D]">Recipe Box</h2>
        <span className="text-sm text-[#6B7B6B]">{recipes.length} recipes</span>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Search recipes..."
          className="flex-1 px-4 py-2 border border-[#D8DCD0] rounded-lg focus:ring-2 focus:ring-[#6B8E6B] focus:border-transparent bg-white"
        />
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc' | 'none')}
          className="px-3 py-2 border border-[#D8DCD0] rounded-lg focus:ring-2 focus:ring-[#6B8E6B] focus:border-transparent bg-white"
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sortedRecipes.map((recipe) => (
            <div
              key={recipe.id}
              className="border border-[#D8DCD0] rounded-lg p-3 hover:border-[#6B8E6B] transition-colors bg-white"
            >
              <div className="flex gap-3">
                {recipe.image_url ? (
                  <img
                    src={recipe.image_url}
                    alt={recipe.title}
                    className="w-20 h-20 object-cover rounded"
                  />
                ) : (
                  <div className="w-20 h-20 bg-[#F0F0E8] rounded flex items-center justify-center text-[#6B7B6B]">
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
              <div className="mt-3 flex gap-2">
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
      )}

      {addToPlanRecipe && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#FAFAF7] rounded-lg p-6 w-80 shadow-xl">
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
