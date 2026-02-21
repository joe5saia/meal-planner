import { lazy, Suspense, useCallback, useState } from 'react';
import type { WeekCount } from './components/WeeklyPlanner';
import { api } from './api/client';
import type { Recipe } from './api/types';
import { decodeHtmlEntities } from './utils/text';

type Tab = 'search' | 'box' | 'planner' | 'grocery';

const RecipeSearch = lazy(async () => {
  const module = await import('./components/RecipeSearch');
  return { default: module.RecipeSearch };
});

const RecipeBox = lazy(async () => {
  const module = await import('./components/RecipeBox');
  return { default: module.RecipeBox };
});

const WeeklyPlanner = lazy(async () => {
  const module = await import('./components/WeeklyPlanner');
  return { default: module.WeeklyPlanner };
});

const GroceryList = lazy(async () => {
  const module = await import('./components/GroceryList');
  return { default: module.GroceryList };
});

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
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

  const handleTabChange = useCallback((tab: Tab) => {
    setActiveTab(tab);
    setIsSidebarOpen(false);
  }, []);

  const handleGenerateGroceryList = useCallback((recipeIds: number[]) => {
    setGroceryRecipeIds(recipeIds);
    setActiveTab('grocery');
    setIsSidebarOpen(false);
  }, []);

  const handleAddToPlan = useCallback(async (recipeId: number, date: string, mealType: string) => {
    try {
      await api.mealPlans.create({ recipe_id: recipeId, date, meal_type: mealType });
      setRefreshTrigger((t) => t + 1);
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

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'search':
        return <RecipeSearch onRecipeSaved={handleRecipeSaved} />;
      case 'box':
        return (
          <RecipeBox
            onSelectRecipe={handleSelectRecipe}
            onRecipeRemoved={handleRecipeRemoved}
            onAddToPlan={handleAddToPlan}
            refreshTrigger={refreshTrigger}
          />
        );
      case 'planner':
        return (
          <WeeklyPlanner
            onGenerateGroceryList={handleGenerateGroceryList}
            weeksToShow={weeksToShow}
            onWeeksToShowChange={setWeeksToShow}
          />
        );
      case 'grocery':
        return <GroceryList recipeIds={groceryRecipeIds} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F5F0]">
      <header className="sticky top-0 z-40 flex items-center justify-between border-b border-white/10 bg-gradient-to-b from-[#6B8E6B] to-[#4A6B4A] px-4 py-3 md:hidden">
        <button
          type="button"
          onClick={() => setIsSidebarOpen(true)}
          className="rounded-md p-2 text-white hover:bg-white/10"
          aria-label="Open navigation menu"
        >
          ☰
        </button>
        <h1 className="text-lg font-bold text-white">Meal Planner</h1>
        <span className="w-8" aria-hidden="true"></span>
      </header>

      <div className="flex min-h-[calc(100vh-61px)] md:min-h-screen">
        {isSidebarOpen && (
          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 z-40 bg-black/45 md:hidden"
            aria-label="Close navigation menu"
          />
        )}

        <aside
          className={`fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] shrink-0 flex-col bg-gradient-to-b from-[#6B8E6B] to-[#4A6B4A] transition-transform md:static md:z-auto md:w-56 md:max-w-none ${
            isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
        >
          <div className="flex items-center justify-between border-b border-white/10 p-4 md:justify-start md:gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 text-lg">
                🥗
              </div>
              <h1 className="text-xl font-bold text-white">Meal Planner</h1>
            </div>
            <button
              type="button"
              onClick={() => setIsSidebarOpen(false)}
              className="rounded-md p-1.5 text-white hover:bg-white/10 md:hidden"
              aria-label="Close navigation menu"
            >
              ✕
            </button>
          </div>

          <nav className="flex-1 p-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => handleTabChange(tab.id)}
                className={`mb-1 flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors ${
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

        <main className="min-w-0 flex-1 overflow-auto p-4 md:p-6">
          <div className="max-w-6xl">
            <Suspense
              fallback={
                <div className="rounded-lg bg-[#FAFAF7] p-6 text-[#6B7B6B] shadow">
                  Loading…
                </div>
              }
            >
              {renderActiveTab()}
            </Suspense>
          </div>

          {selectedRecipe && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
              <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-[#FAFAF7] p-4 md:p-6">
                <div className="mb-4 flex items-start justify-between gap-3">
                  <h2 className="text-xl font-semibold">{decodeHtmlEntities(selectedRecipe.title)}</h2>
                  <button
                    type="button"
                    onClick={() => setSelectedRecipe(null)}
                    className="text-2xl text-gray-400 hover:text-gray-600"
                    aria-label="Close recipe details"
                  >
                    ×
                  </button>
                </div>

                {selectedRecipe.image_url && (
                  <img
                    src={selectedRecipe.image_url}
                    alt={selectedRecipe.title}
                    width={960}
                    height={540}
                    loading="eager"
                    decoding="async"
                    className="mb-4 h-48 w-full rounded-lg object-cover"
                  />
                )}

                {selectedRecipe.description && (
                  <p className="mb-4 text-gray-600">{selectedRecipe.description}</p>
                )}

                <div className="mb-4 flex flex-wrap gap-4 text-sm text-gray-500">
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

                <h3 className="mb-2 font-medium">Ingredients</h3>
                <ul className="mb-4 space-y-1 text-sm text-gray-600">
                  {selectedRecipe.ingredients.map((ing, i) => (
                    <li key={i}>• {ing}</li>
                  ))}
                </ul>

                {selectedRecipe.instructions && selectedRecipe.instructions.length > 0 && (
                  <>
                    <h3 className="mb-2 font-medium">Instructions</h3>
                    <ol className="list-inside list-decimal space-y-2 text-sm text-gray-600">
                      {selectedRecipe.instructions.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </>
                )}

                <div className="mt-6 border-t pt-4">
                  <a
                    href={selectedRecipe.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-[#6B8E6B] hover:text-[#4A6B4A]"
                  >
                    View original recipe →
                  </a>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
