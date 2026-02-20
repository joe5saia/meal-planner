import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import type { GroceryList as GroceryListType, GroceryItem } from '../api/types';
import { decodeHtmlEntities } from '../utils/text';

const SECTION_ORDER = [
  'Produce',
  'Meat & Seafood',
  'Dairy',
  'Bakery & Deli',
  'Frozen',
  'Grocery',
  'Canned & Jarred',
  'Spices & Seasonings',
  'Other'
];

type SortOption = 'alpha-asc' | 'alpha-desc' | 'by-section';

interface GroceryListProps {
  recipeIds?: number[];
}

export function GroceryList({ recipeIds }: GroceryListProps) {
  const [groceryList, setGroceryList] = useState<GroceryListType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkedItems, setCheckedItems] = useState<Set<string>>(new Set());
  const [deletedItems, setDeletedItems] = useState<Set<string>>(new Set());
  const [sortOption, setSortOption] = useState<SortOption>('alpha-asc');

  useEffect(() => {
    if (recipeIds && recipeIds.length > 0) {
      fetchGroceryList();
    }
  }, [recipeIds]);

  const fetchGroceryList = async () => {
    if (!recipeIds || recipeIds.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      const list = await api.grocery.generate(recipeIds);
      setGroceryList(list);
      setCheckedItems(new Set());
      setDeletedItems(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate list');
    } finally {
      setLoading(false);
    }
  };

  const toggleItem = (name: string) => {
    const newChecked = new Set(checkedItems);
    if (newChecked.has(name)) {
      newChecked.delete(name);
    } else {
      newChecked.add(name);
    }
    setCheckedItems(newChecked);
  };

  const deleteItem = (name: string) => {
    setDeletedItems(prev => new Set([...prev, name]));
    setCheckedItems(prev => {
      const newSet = new Set(prev);
      newSet.delete(name);
      return newSet;
    });
  };

  const deleteAllChecked = () => {
    setDeletedItems(prev => new Set([...prev, ...checkedItems]));
    setCheckedItems(new Set());
  };

  const formatQuantity = (item: GroceryItem) => {
    const quantityParts = [];
    if (item.quantity) quantityParts.push(item.quantity);
    if (item.unit) quantityParts.push(item.unit);
    
    if (quantityParts.length > 0) {
      return `(${quantityParts.join(' ')})`;
    }
    return null;
  };

  const formatItemForClipboard = (item: GroceryItem) => {
    const qty = formatQuantity(item);
    return qty ? `${item.name} ${qty}` : item.name;
  };

  const visibleItems = useMemo(() => {
    if (!groceryList) return [];
    return groceryList.items.filter(item => !deletedItems.has(item.name));
  }, [groceryList, deletedItems]);

  const sortedItems = useMemo(() => {
    const items = [...visibleItems];
    
    switch (sortOption) {
      case 'alpha-asc':
        return items.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
      case 'alpha-desc':
        return items.sort((a, b) => b.name.toLowerCase().localeCompare(a.name.toLowerCase()));
      case 'by-section':
        return items.sort((a, b) => {
          const indexA = SECTION_ORDER.indexOf(a.category) ?? SECTION_ORDER.length;
          const indexB = SECTION_ORDER.indexOf(b.category) ?? SECTION_ORDER.length;
          if (indexA !== indexB) return indexA - indexB;
          return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
        });
      default:
        return items;
    }
  }, [visibleItems, sortOption]);

  const groupedItems = useMemo(() => {
    if (sortOption !== 'by-section') return null;
    
    const groups: Record<string, GroceryItem[]> = {};
    for (const item of sortedItems) {
      const section = item.category || 'Other';
      if (!groups[section]) groups[section] = [];
      groups[section].push(item);
    }
    return groups;
  }, [sortedItems, sortOption]);

  const copyToClipboard = () => {
    if (!groceryList) return;

    const text = sortedItems
      .map((item) => formatItemForClipboard(item))
      .join('\n');

    navigator.clipboard.writeText(text);
  };

  if (!recipeIds || recipeIds.length === 0) {
    return (
      <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold text-[#2D3B2D] mb-4">Grocery List</h2>
        <p className="text-[#6B7B6B] text-center py-8">
          Select recipes from the weekly planner to generate a grocery list
        </p>
      </div>
    );
  }

  const renderItem = (item: GroceryItem, index: number) => {
    const qty = formatQuantity(item);
    const isChecked = checkedItems.has(item.name);
    
    return (
      <div
        key={index}
        className="flex items-center gap-3 py-2 px-1 rounded-md hover:bg-[#F0F0E8] group transition-colors"
      >
        <input
          type="checkbox"
          checked={isChecked}
          onChange={() => toggleItem(item.name)}
          className="h-[18px] w-[18px] accent-[#6B8E6B] cursor-pointer shrink-0"
        />
        <span
          className={`flex-1 text-[0.9rem] ${
            isChecked ? 'line-through text-[#6B7B6B]' : 'text-[#2D3B2D]'
          }`}
        >
          {item.name}
        </span>
        {qty && (
          <span className="text-[0.85rem] font-medium text-[#6B7B6B] shrink-0">
            {qty}
          </span>
        )}
        <button
          onClick={() => deleteItem(item.name)}
          className="opacity-0 group-hover:opacity-100 text-[#6B7B6B] hover:text-[#B87A5A] transition-opacity p-1 text-lg"
          title="Remove from list"
        >
          ×
        </button>
      </div>
    );
  };

  return (
    <div className="bg-[#FAFAF7] rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-[1.15rem] font-semibold text-[#2D3B2D]">Grocery List</h2>
        {groceryList && (
          <div className="flex items-center gap-2">
            {checkedItems.size > 0 && (
              <button
                onClick={deleteAllChecked}
                className="px-3 py-1.5 bg-[#B87A5A] text-white rounded-md text-[0.8rem] font-medium hover:bg-[#A06848] transition-colors"
              >
                Delete Checked ({checkedItems.size})
              </button>
            )}
            <select
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value as SortOption)}
              className="text-[0.8rem] border border-[#D8DCD0] rounded-md px-2.5 py-1.5 bg-[#FAFAF7] text-[#2D3B2D]"
            >
              <option value="alpha-asc">A to Z</option>
              <option value="alpha-desc">Z to A</option>
              <option value="by-section">By Store Section</option>
            </select>
            <button
              onClick={copyToClipboard}
              className="px-3 py-1.5 border border-[#D8DCD0] rounded-md text-[0.8rem] text-[#6B7B6B] hover:border-[#6B8E6B] hover:text-[#6B8E6B] transition-colors"
            >
              Copy to clipboard
            </button>
          </div>
        )}
      </div>

      {loading && <div className="text-[#6B7B6B]">Generating list...</div>}

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg mb-4">{error}</div>
      )}

      {groceryList && (
        <>
          <div className="bg-[#F0F0E8] rounded-lg px-4 py-3 mb-4 text-[0.85rem] text-[#6B7B6B]">
            📋 From {groceryList.recipe_count} recipe(s): {groceryList.recipe_titles.map(t => decodeHtmlEntities(t)).join(', ')}
          </div>

          {sortOption === 'by-section' && groupedItems ? (
            <div className="space-y-5">
              {SECTION_ORDER.map((section) => {
                const items = groupedItems[section];
                if (!items || items.length === 0) return null;
                return (
                  <div key={section}>
                    <h3 className="flex items-center gap-2 text-[0.8rem] font-semibold text-[#4A6B4A] pb-1.5 mb-1.5 border-b-2 border-[#D4E4D4]">
                      <span className="w-1 h-4 bg-[#6B8E6B] rounded-sm"></span>
                      {section}
                    </h3>
                    <div className="space-y-0">
                      {items.map((item, i) => renderItem(item, i))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="space-y-2">
              {sortedItems.map((item, i) => renderItem(item, i))}
            </div>
          )}

          <div className="mt-4 pt-4 border-t border-[#D8DCD0] text-[0.85rem] text-[#6B7B6B] flex justify-between">
            <span>{checkedItems.size} of {visibleItems.length} items checked</span>
            {deletedItems.size > 0 && (
              <span>{deletedItems.size} item(s) removed</span>
            )}
          </div>
        </>
      )}
    </div>
  );
}
