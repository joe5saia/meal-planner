import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import type { MealPlan, Recipe } from '../api/types';
import { decodeHtmlEntities } from '../utils/text';

const MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'dessert', 'other'] as const;
type MealType = typeof MEAL_TYPES[number];

const MEAL_TYPE_COLORS: Record<MealType, { bg: string; text: string; border: string }> = {
  breakfast: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-300' },
  lunch: { bg: 'bg-sky-100', text: 'text-sky-800', border: 'border-sky-300' },
  dinner: { bg: 'bg-[#4A6B4A]', text: 'text-white', border: 'border-[#3A5A3A]' },
  dessert: { bg: 'bg-rose-100', text: 'text-rose-800', border: 'border-rose-300' },
  other: { bg: 'bg-stone-100', text: 'text-stone-700', border: 'border-stone-300' },
};

interface RecipeComboboxProps {
  recipes: Recipe[];
  onSelectRecipe: (recipeId: number, mealType: MealType) => void;
  onAddPlaceholder: (text: string, mealType: MealType) => void;
}

function RecipeCombobox({ recipes, onSelectRecipe, onAddPlaceholder }: RecipeComboboxProps) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedMealType, setSelectedMealType] = useState<MealType>('dinner');
  const [showMealTypeMenu, setShowMealTypeMenu] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = recipes.filter(r =>
    r.title.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
        setShowMealTypeMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (recipeId: number) => {
    onSelectRecipe(recipeId, selectedMealType);
    setQuery('');
    setIsOpen(false);
  };

  const handleAddAsPlaceholder = () => {
    if (query.trim()) {
      onAddPlaceholder(query.trim(), selectedMealType);
      setQuery('');
      setIsOpen(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && query.trim()) {
      if (filtered.length > 0) {
        handleSelect(filtered[0].id);
      } else {
        handleAddAsPlaceholder();
      }
    }
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  const colors = MEAL_TYPE_COLORS[selectedMealType];

  return (
    <div ref={containerRef} className="relative mt-2">
      <div className="flex gap-1">
        <div className="relative">
          <button
            onClick={() => setShowMealTypeMenu(!showMealTypeMenu)}
            className={`text-xs px-1.5 py-1 rounded-l border ${colors.bg} ${colors.text} ${colors.border}`}
            title="Select meal type"
          >
            {selectedMealType.charAt(0).toUpperCase()}
          </button>
          {showMealTypeMenu && (
            <div className="absolute top-full left-0 mt-1 bg-white border border-[#D8DCD0] rounded shadow-lg z-20 min-w-24">
              {MEAL_TYPES.map(type => (
                <button
                  key={type}
                  onClick={() => {
                    setSelectedMealType(type);
                    setShowMealTypeMenu(false);
                  }}
                  className={`block w-full text-left text-xs px-2 py-1 hover:bg-[#F0F0E8] ${
                    selectedMealType === type ? 'font-semibold' : ''
                  }`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="+ Add meal"
          className="flex-1 text-xs border border-[#D8DCD0] rounded-r p-1 min-w-0"
        />
      </div>
      {isOpen && (query || recipes.length > 0) && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-[#D8DCD0] rounded shadow-lg z-10 max-h-48 overflow-y-auto">
          {filtered.length > 0 ? (
            filtered.map(r => (
              <button
                key={r.id}
                onClick={() => handleSelect(r.id)}
                className="block w-full text-left text-xs px-2 py-1.5 hover:bg-[#F0F0E8] truncate"
              >
                {r.title}
              </button>
            ))
          ) : query.trim() ? (
            <button
              onClick={handleAddAsPlaceholder}
              className="block w-full text-left text-xs px-2 py-1.5 hover:bg-[#F0F0E8] italic text-[#6B7B6B]"
            >
              Add "{query}" as note
            </button>
          ) : (
            <div className="text-xs px-2 py-1.5 text-[#6B7B6B]">No recipes saved</div>
          )}
        </div>
      )}
    </div>
  );
}

export type WeekCount = 1 | 2 | 3 | 4;

interface WeeklyPlannerProps {
  onGenerateGroceryList?: (recipeIds: number[]) => void;
  weeksToShow: WeekCount;
  onWeeksToShowChange: (weeks: WeekCount) => void;
}

export function WeeklyPlanner({ onGenerateGroceryList, weeksToShow, onWeeksToShowChange }: WeeklyPlannerProps) {
  const [mealPlans, setMealPlans] = useState<MealPlan[]>([]);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDates, setSelectedDates] = useState<Set<string>>(new Set());
  const [weekStart, setWeekStart] = useState(() => {
    const today = new Date();
    const day = today.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
    const daysSinceSat = (day + 1) % 7; // Sat=0, Sun=1, Mon=2, ...
    const start = new Date(today);
    start.setDate(today.getDate() - daysSinceSat);
    return start;
  });

  const totalDays = 7 * weeksToShow;
  const allDays = Array.from({ length: totalDays }, (_, i) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    return date;
  });

  const formatDate = (date: Date) => date.toISOString().split('T')[0];

  const fetchData = async () => {
    setLoading(true);
    try {
      const startDate = formatDate(allDays[0]);
      const endDate = formatDate(allDays[allDays.length - 1]);
      const [plans, recipeList] = await Promise.all([
        api.mealPlans.list(startDate, endDate),
        api.recipes.getBox(),
      ]);
      setMealPlans(plans);
      setRecipes(recipeList);
    } catch (err) {
      console.error('Failed to load meal plans:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [weekStart, weeksToShow]);

  const handleAddMeal = async (date: Date, recipeId: number, mealType: MealType) => {
    try {
      const plan = await api.mealPlans.create({
        recipe_id: recipeId,
        date: formatDate(date),
        meal_type: mealType,
      });
      setMealPlans([...mealPlans, plan]);
    } catch (err) {
      console.error('Failed to add meal:', err);
    }
  };

  const handleAddPlaceholder = async (date: Date, text: string, mealType: MealType) => {
    try {
      const plan = await api.mealPlans.create({
        placeholder_text: text,
        date: formatDate(date),
        meal_type: mealType,
      });
      setMealPlans([...mealPlans, plan]);
    } catch (err) {
      console.error('Failed to add placeholder:', err);
    }
  };

  const handleUpdateMealType = async (planId: number, newMealType: MealType) => {
    try {
      await api.mealPlans.update(planId, { meal_type: newMealType });
      setMealPlans(mealPlans.map(p => 
        p.id === planId ? { ...p, meal_type: newMealType } : p
      ));
    } catch (err) {
      console.error('Failed to update meal type:', err);
    }
  };

  const handleRemoveMeal = async (planId: number) => {
    try {
      await api.mealPlans.delete(planId);
      setMealPlans(mealPlans.filter((p) => p.id !== planId));
    } catch (err) {
      console.error('Failed to remove meal:', err);
    }
  };

  const handlePrevPeriod = () => {
    const newStart = new Date(weekStart);
    newStart.setDate(newStart.getDate() - 7);
    setWeekStart(newStart);
  };

  const handleNextPeriod = () => {
    const newStart = new Date(weekStart);
    newStart.setDate(newStart.getDate() + 7);
    setWeekStart(newStart);
  };

  const toggleDateSelection = (date: Date) => {
    const dateStr = formatDate(date);
    setSelectedDates(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dateStr)) {
        newSet.delete(dateStr);
      } else {
        newSet.add(dateStr);
      }
      return newSet;
    });
  };

  const selectAllDates = () => {
    setSelectedDates(new Set(allDays.map(d => formatDate(d))));
  };

  const deselectAllDates = () => {
    setSelectedDates(new Set());
  };

  const selectedMealsCount = mealPlans.filter(
    p => p.recipe_id != null && selectedDates.has(p.date)
  ).length;

  const handleGenerateList = () => {
    const recipeIds = [...new Set(
      mealPlans
        .filter((p): p is MealPlan & { recipe_id: number } =>
          p.recipe_id != null && selectedDates.has(p.date)
        )
        .map((p) => p.recipe_id)
    )];
    onGenerateGroceryList?.(recipeIds);
  };

  const getMealsForDate = (date: Date) =>
    mealPlans.filter((p) => p.date === formatDate(date));

  const dayNames = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri'];

  return (
    <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold text-[#2D3B2D]">Weekly Planner</h2>
          <div className="flex border border-[#D8DCD0] rounded overflow-hidden">
            {([1, 2, 3, 4] as WeekCount[]).map(w => (
              <button
                key={w}
                onClick={() => onWeeksToShowChange(w)}
                className={`px-2 py-1 text-xs ${
                  weeksToShow === w
                    ? 'bg-[#6B8E6B] text-white'
                    : 'bg-white text-[#6B7B6B] hover:bg-[#F0F0E8]'
                }`}
              >
                {w}W
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevPeriod}
            className="p-2 hover:bg-[#F0F0E8] rounded text-[#2D3B2D]"
          >
            ←
          </button>
          <span className="text-base font-medium text-[#2D3B2D]">
            {allDays[0].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} -{' '}
            {allDays[allDays.length - 1].toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </span>
          <button
            onClick={handleNextPeriod}
            className="p-2 hover:bg-[#F0F0E8] rounded text-[#2D3B2D]"
          >
            →
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-[#6B7B6B]">Loading...</div>
      ) : (
        <>
          <div className="grid grid-cols-7 gap-2 mb-4">
            {allDays.map((date, i) => {
              const meals = getMealsForDate(date);
              const isToday = formatDate(date) === formatDate(new Date());
              const isSelected = selectedDates.has(formatDate(date));
              const dayIndex = i % 7;

              return (
                <div
                  key={i}
                  className={`border rounded-lg p-2 min-h-44 ${
                    isSelected 
                      ? 'bg-[#D4E4D4] border-[#6B8E6B]' 
                      : isToday 
                        ? 'border-[#6B8E6B] bg-[#F5F5F0]' 
                        : 'border-[#D8DCD0] bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={`text-sm font-medium ${isSelected ? 'text-[#2D3B2D]' : 'text-[#6B7B6B]'}`}>
                      {dayNames[dayIndex]}
                      <span className={`ml-1 ${isSelected ? 'text-[#4A6B4A]' : 'text-[#6B7B6B]'}`}>{date.getDate()}</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleDateSelection(date)}
                      className="h-4 w-4 text-[#6B8E6B] rounded cursor-pointer accent-[#6B8E6B]"
                      title="Include in grocery list"
                    />
                  </div>

                  <div className="space-y-1">
                    {meals.map((meal) => {
                      const mealType = (meal.meal_type || 'other') as MealType;
                      const colors = MEAL_TYPE_COLORS[mealType] || MEAL_TYPE_COLORS.other;
                      const isPlaceholder = !meal.recipe_id;
                      
                      return (
                        <div
                          key={meal.id}
                          className={`text-xs rounded p-1 flex justify-between items-start ${colors.bg} ${colors.text}`}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1">
                              <select
                                value={mealType}
                                onChange={(e) => handleUpdateMealType(meal.id, e.target.value as MealType)}
                                className={`text-[10px] px-0.5 rounded border-0 ${colors.bg} ${colors.text} cursor-pointer`}
                                title="Change meal type"
                              >
                                {MEAL_TYPES.map(t => (
                                  <option key={t} value={t}>
                                    {t.charAt(0).toUpperCase()}
                                  </option>
                                ))}
                              </select>
                              <span className={`truncate ${isPlaceholder ? 'italic' : ''}`}>
                                {isPlaceholder ? meal.placeholder_text : (meal.recipe_title ? decodeHtmlEntities(meal.recipe_title) : '')}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveMeal(meal.id)}
                            className={`ml-1 ${colors.text} hover:text-red-600`}
                          >
                            ×
                          </button>
                        </div>
                      );
                    })}
                  </div>

                  <RecipeCombobox
                    recipes={recipes}
                    onSelectRecipe={(recipeId, mealType) => handleAddMeal(date, recipeId, mealType)}
                    onAddPlaceholder={(text, mealType) => handleAddPlaceholder(date, text, mealType)}
                  />
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={selectAllDates}
                className="text-sm text-[#6B7B6B] hover:text-[#2D3B2D] px-2 py-1"
              >
                Select All
              </button>
              <span className="text-[#D8DCD0]">|</span>
              <button
                onClick={deselectAllDates}
                className="text-sm text-[#6B7B6B] hover:text-[#2D3B2D] px-2 py-1"
              >
                Deselect All
              </button>
              <span className="text-sm text-[#6B7B6B] ml-2">
                {selectedDates.size} day(s) selected
              </span>
            </div>
            <button
              onClick={handleGenerateList}
              disabled={selectedDates.size === 0 || selectedMealsCount === 0}
              className="px-4 py-2 bg-[#6B8E6B] text-white rounded-lg hover:bg-[#4A6B4A] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Generate Grocery List ({selectedDates.size} days, {selectedMealsCount} meals)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
