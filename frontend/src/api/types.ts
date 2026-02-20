export interface Recipe {
  id: number;
  url: string;
  title: string;
  description?: string;
  image_url?: string;
  ingredients: string[];
  instructions?: string[];
  prep_time?: string;
  cook_time?: string;
  total_time?: string;
  servings?: string;
  source_site: string;
  created_at: string;
  in_recipe_box: boolean;
}

export interface ScrapedRecipe {
  url: string;
  title: string;
  description?: string;
  image_url?: string;
  ingredients: string[];
  instructions?: string[];
  prep_time?: string;
  cook_time?: string;
  total_time?: string;
  servings?: string;
  source_site: string;
  requires_manual_entry: boolean;
  error_message?: string;
}

export interface MealPlan {
  id: number;
  recipe_id?: number;
  recipe_title?: string;
  recipe_image_url?: string;
  placeholder_text?: string;
  date: string;
  meal_type?: string;
  created_at: string;
}

export interface MealPlanCreate {
  recipe_id?: number;
  placeholder_text?: string;
  date: string;
  meal_type?: string;
}

export interface MealPlanUpdate {
  meal_type?: string;
}

export interface GroceryItem {
  name: string;
  quantity?: string;
  unit?: string;
  category: string;
  original_strings: string[];
}

export interface GroceryList {
  items: GroceryItem[];
  recipe_count: number;
  recipe_titles: string[];
}
