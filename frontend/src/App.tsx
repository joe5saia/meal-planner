import { useState, useCallback } from 'react';
import { RecipeSearch } from './components/RecipeSearch';
import { RecipeBox } from './components/RecipeBox';
import { WeeklyPlanner, type WeekCount } from './components/WeeklyPlanner';
import { GroceryList } from './components/GroceryList';
import { api } from './api/client';
import type { Recipe } from './api/types';
import { decodeHtmlEntities } from './utils/text';

type Tab = 'search' | 'box' | 'planner' | 'grocery';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [groceryRecipeIds, setGroceryRecipeIds] = useState<number[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [weeksToShow, setWeeksToShow] = useState<WeekCount>(1);

  const handleRecipeSaved = useCallback(async () => {
    setRefreshTrigger((t) => t + 1);
  }, []);

  const handleRecipeRemoved = useCallback(() => {
    setRefreshTrigger((t) => t + 1);
    setGroceryRecipeIds([]);
  }, []);

  const handleSelectRecipe = useCallback(async (recipe: Recipe) => {
    setSelectedRecipe(recipe);
    if (!recipe.in_recipe_box) {
      try {
        await api.recipes.addToBox(recipe.id);
        setRefreshTrigger((t) => t + 1);
      } catch (err) {
        console.error('Failed to add to box:', err);
      }
    }
  }, []);

  const handleGenerateGroceryList = useCallback((recipeIds: number[]) => {
    setGroceryRecipeIds(recipeIds);
    setActiveTab('grocery');
  }, []);

  const handleAddToPlan = useCallback(async (recipeId: number, date: string, mealType: string) => {
    try {
      await api.mealPlans.create({ recipe_id: recipeId, date, meal_type: mealType });
      setRefreshTrigger(t => t + 1);
    } catch (err) {
      console.error('Failed to add to plan:', err);
    }
  }, []);

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'search', label: 'Add Recipe', icon: '+' },
    { id: 'box', label: 'Recipe Box', icon: '📦' },
    { id: 'planner', label: 'Weekly Planner', icon: '📅' },
    { id: 'grocery', label: 'Grocery List', icon: '🛒' },
  ];

  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-gradient-to-b from-[#6B8E6B] to-[#4A6B4A] flex flex-col shrink-0">
        <div className="p-4 border-b border-white/10 flex items-center gap-3">
          <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center text-lg">
            🥗
          </div>
          <h1 className="text-xl font-bold text-white">Meal Planner</h1>
        </div>
        <nav className="flex-1 p-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 transition-colors flex items-center gap-2.5 ${
                activeTab === tab.id
                  ? 'bg-white/20 text-white font-medium'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`}
            >
              <span className="text-base">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="flex-1 bg-[#F5F5F0] p-6 overflow-auto">
        <div className="max-w-6xl">
          {activeTab === 'search' && (
            <RecipeSearch onRecipeSaved={handleRecipeSaved} />
          )}

          {activeTab === 'box' && (
            <RecipeBox
              onSelectRecipe={handleSelectRecipe}
              onRecipeRemoved={handleRecipeRemoved}
              onAddToPlan={handleAddToPlan}
              refreshTrigger={refreshTrigger}
            />
          )}

          {activeTab === 'planner' && (
            <WeeklyPlanner
              onGenerateGroceryList={handleGenerateGroceryList}
              weeksToShow={weeksToShow}
              onWeeksToShowChange={setWeeksToShow}
            />
          )}

          {activeTab === 'grocery' && <GroceryList recipeIds={groceryRecipeIds} />}
        </div>

        {selectedRecipe && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-[#FAFAF7] rounded-lg max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-semibold">{decodeHtmlEntities(selectedRecipe.title)}</h2>
                <button
                  onClick={() => setSelectedRecipe(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>

              {selectedRecipe.image_url && (
                <img
                  src={selectedRecipe.image_url}
                  alt={selectedRecipe.title}
                  className="w-full h-48 object-cover rounded-lg mb-4"
                />
              )}

              {selectedRecipe.description && (
                <p className="text-gray-600 mb-4">{selectedRecipe.description}</p>
              )}

              <div className="flex gap-4 text-sm text-gray-500 mb-4">
                {selectedRecipe.prep_time && (
                  <span>Prep: {selectedRecipe.prep_time}</span>
                )}
                {selectedRecipe.cook_time && (
                  <span>Cook: {selectedRecipe.cook_time}</span>
                )}
                {selectedRecipe.servings && (
                  <span>Serves: {selectedRecipe.servings}</span>
                )}
              </div>

              <h3 className="font-medium mb-2">Ingredients</h3>
              <ul className="text-sm text-gray-600 space-y-1 mb-4">
                {selectedRecipe.ingredients.map((ing, i) => (
                  <li key={i}>• {ing}</li>
                ))}
              </ul>

              {selectedRecipe.instructions && selectedRecipe.instructions.length > 0 && (
                <>
                  <h3 className="font-medium mb-2">Instructions</h3>
                  <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
                    {selectedRecipe.instructions.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </>
              )}

              <div className="mt-6 pt-4 border-t">
                <a
                  href={selectedRecipe.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#6B8E6B] hover:text-[#4A6B4A] text-sm"
                >
                  View original recipe →
                </a>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
