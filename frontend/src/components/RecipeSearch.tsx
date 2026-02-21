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

      <form onSubmit={handleScrape} className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste recipe URL..."
          className="w-full flex-1 rounded-lg border border-[#D8DCD0] bg-white px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-[#6B8E6B]"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[#6B8E6B] px-6 py-2 text-white hover:bg-[#4A6B4A] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {loading ? 'Scraping...' : 'Get Recipe'}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!scrapedRecipe || saving}
          className="w-full rounded-lg bg-[#6B8E6B] px-6 py-2 text-white hover:bg-[#4A6B4A] disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
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
          <div className="flex flex-col gap-4 sm:flex-row">
            {scrapedRecipe.image_url && (
              <img
                src={scrapedRecipe.image_url}
                alt={scrapedRecipe.title}
                width={320}
                height={180}
                loading="lazy"
                decoding="async"
                className="h-48 w-full rounded-lg object-cover sm:h-32 sm:w-32"
              />
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-[#2D3B2D]">{scrapedRecipe.title}</h3>
              {scrapedRecipe.description && (
                <p className="text-[#6B7B6B] text-sm mt-1 line-clamp-2">
                  {scrapedRecipe.description}
                </p>
              )}
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-[#6B7B6B]">
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
