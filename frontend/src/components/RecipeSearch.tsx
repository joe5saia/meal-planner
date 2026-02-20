import { useState } from 'react';
import { api } from '../api/client';
import type { ScrapedRecipe } from '../api/types';

interface RecipeSearchProps {
  onRecipeSaved?: () => void;
}

export function RecipeSearch({ onRecipeSaved }: RecipeSearchProps) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scrapedRecipe, setScrapedRecipe] = useState<ScrapedRecipe | null>(null);
  const [saving, setSaving] = useState(false);

  const handleScrape = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);
    setScrapedRecipe(null);

    try {
      const recipe = await api.recipes.scrape(url);
      setScrapedRecipe(recipe);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to scrape recipe');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!scrapedRecipe) return;

    setSaving(true);
    setError(null);
    try {
      const savedRecipe = await api.recipes.save(scrapedRecipe);
      await api.recipes.addToBox(savedRecipe.id);
      setScrapedRecipe(null);
      setUrl('');
      onRecipeSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save recipe');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
      <h2 className="text-xl font-semibold text-[#2D3B2D] mb-4">Add Recipe</h2>

      <form onSubmit={handleScrape} className="flex gap-2 mb-4">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste recipe URL..."
          className="flex-1 px-4 py-2 border border-[#D8DCD0] rounded-lg focus:ring-2 focus:ring-[#6B8E6B] focus:border-transparent bg-white"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2 bg-[#6B8E6B] text-white rounded-lg hover:bg-[#4A6B4A] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Scraping...' : 'Get Recipe'}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!scrapedRecipe || saving}
          className="px-6 py-2 bg-[#6B8E6B] text-white rounded-lg hover:bg-[#4A6B4A] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Recipe'}
        </button>
      </form>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-4">
          {error}
        </div>
      )}

      {scrapedRecipe && (
        <div className="border border-[#D8DCD0] rounded-lg p-4 bg-white">
          <div className="flex gap-4">
            {scrapedRecipe.image_url && (
              <img
                src={scrapedRecipe.image_url}
                alt={scrapedRecipe.title}
                className="w-32 h-32 object-cover rounded-lg"
              />
            )}
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-[#2D3B2D]">{scrapedRecipe.title}</h3>
              {scrapedRecipe.description && (
                <p className="text-[#6B7B6B] text-sm mt-1 line-clamp-2">
                  {scrapedRecipe.description}
                </p>
              )}
              <div className="flex gap-4 mt-2 text-sm text-[#6B7B6B]">
                {scrapedRecipe.prep_time && <span>Prep: {scrapedRecipe.prep_time}</span>}
                {scrapedRecipe.cook_time && <span>Cook: {scrapedRecipe.cook_time}</span>}
                {scrapedRecipe.servings && <span>Serves: {scrapedRecipe.servings}</span>}
              </div>
              <p className="text-sm text-[#6B7B6B] mt-1">
                Source: {scrapedRecipe.source_site}
              </p>
            </div>
          </div>

          {scrapedRecipe.requires_manual_entry && (
            <div className="mt-4 p-3 bg-amber-50 text-amber-700 rounded-lg text-sm">
              {scrapedRecipe.error_message || 'Some recipe data could not be extracted automatically.'}
            </div>
          )}

          <div className="mt-4">
            <h4 className="font-medium text-[#2D3B2D] mb-2">Ingredients ({scrapedRecipe.ingredients.length})</h4>
            <ul className="text-sm text-[#6B7B6B] space-y-1 max-h-40 overflow-y-auto">
              {scrapedRecipe.ingredients.map((ing, i) => (
                <li key={i}>• {ing}</li>
              ))}
            </ul>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={() => setScrapedRecipe(null)}
              className="px-4 py-2 bg-[#F0F0E8] text-[#2D3B2D] rounded-lg hover:bg-[#D8DCD0]"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
