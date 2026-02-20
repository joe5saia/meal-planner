import type {
  Recipe,
  ScrapedRecipe,
  MealPlan,
  MealPlanCreate,
  MealPlanUpdate,
  GroceryList,
} from './types';

const API_BASE = '/api';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  recipes: {
    scrape: (url: string) =>
      fetchJson<ScrapedRecipe>(`${API_BASE}/recipes/scrape`, {
        method: 'POST',
        body: JSON.stringify({ url }),
      }),

    list: () => fetchJson<Recipe[]>(`${API_BASE}/recipes`),

    get: (id: number) => fetchJson<Recipe>(`${API_BASE}/recipes/${id}`),

    save: (recipe: ScrapedRecipe) =>
      fetchJson<Recipe>(`${API_BASE}/recipes`, {
        method: 'POST',
        body: JSON.stringify(recipe),
      }),

    delete: (id: number) =>
      fetchJson<{ message: string }>(`${API_BASE}/recipes/${id}`, {
        method: 'DELETE',
      }),

    addToBox: (id: number) =>
      fetchJson<{ message: string }>(`${API_BASE}/recipes/${id}/add-to-box`, {
        method: 'POST',
      }),

    removeFromBox: (id: number) =>
      fetchJson<{ message: string }>(`${API_BASE}/recipes/${id}/remove-from-box`, {
        method: 'DELETE',
      }),

    getBox: () => fetchJson<Recipe[]>(`${API_BASE}/recipes/box/all`),
  },

  mealPlans: {
    list: (startDate?: string, endDate?: string) => {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      const query = params.toString();
      return fetchJson<MealPlan[]>(`${API_BASE}/meal-plans${query ? `?${query}` : ''}`);
    },

    create: (plan: MealPlanCreate) =>
      fetchJson<MealPlan>(`${API_BASE}/meal-plans`, {
        method: 'POST',
        body: JSON.stringify(plan),
      }),

    update: (id: number, plan: MealPlanUpdate) =>
      fetchJson<MealPlan>(`${API_BASE}/meal-plans/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(plan),
      }),

    delete: (id: number) =>
      fetchJson<{ message: string }>(`${API_BASE}/meal-plans/${id}`, {
        method: 'DELETE',
      }),
  },

  grocery: {
    generate: (recipeIds?: number[], startDate?: string, endDate?: string) =>
      fetchJson<GroceryList>(`${API_BASE}/grocery-list`, {
        method: 'POST',
        body: JSON.stringify({
          recipe_ids: recipeIds,
          start_date: startDate,
          end_date: endDate,
        }),
      }),
  },
};
