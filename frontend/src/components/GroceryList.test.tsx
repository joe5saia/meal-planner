import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { GroceryList } from './GroceryList';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    grocery: {
      generate: vi.fn(),
    },
  },
}));

const mockGroceryList = {
  items: [
    { name: 'apple', quantity: '3', unit: null, category: 'Produce', original_strings: ['3 apples'] },
    { name: 'butter', quantity: '1', unit: 'cup', category: 'Dairy', original_strings: ['1 cup butter'] },
    { name: 'chicken breast', quantity: '2', unit: 'pound', category: 'Meat & Seafood', original_strings: ['2 pounds chicken breast'] },
    { name: 'cumin', quantity: '1', unit: 'teaspoon', category: 'Spices & Seasonings', original_strings: ['1 teaspoon cumin'] },
  ],
  recipe_count: 2,
  recipe_titles: ['Recipe One', 'Recipe Two'],
};

function getItemRow(name: string): HTMLElement {
  const itemLabel = screen.getByText(new RegExp(`^${name}$`, 'i'));
  const row = itemLabel.closest('div[class*="group transition-colors"]');
  expect(row).toBeTruthy();
  return row as HTMLElement;
}

async function clickRemoveItem(user: ReturnType<typeof userEvent.setup>, name: string): Promise<void> {
  const row = getItemRow(name);
  const deleteButton = row.querySelector('button[title="Remove from list"]');
  expect(deleteButton).toBeTruthy();
  await user.click(deleteButton as HTMLButtonElement);
}

function getRenderedItemNames(): string[] {
  const checkboxes = screen.getAllByRole('checkbox');
  return checkboxes.map((checkbox) => {
    const row = checkbox.closest('div[class*="group transition-colors"]');
    const itemLabel = row?.querySelector('span[class*="flex-1"]');
    return itemLabel?.textContent ?? '';
  });
}

describe('GroceryList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.grocery.generate as ReturnType<typeof vi.fn>).mockResolvedValue(mockGroceryList);
  });

  it('renders empty state when no recipe IDs provided', () => {
    render(<GroceryList />);
    expect(screen.getByText(/select recipes from the weekly planner/i)).toBeInTheDocument();
  });

  it('fetches and displays grocery list when recipe IDs provided', async () => {
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    expect(screen.getByText(/butter/i)).toBeInTheDocument();
    expect(screen.getByText(/chicken breast/i)).toBeInTheDocument();
    expect(screen.getByText(/cumin/i)).toBeInTheDocument();
  });

  it('displays item in correct format: name (quantity unit)', async () => {
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/^butter$/i)).toBeInTheDocument();
      expect(screen.getByText(/^\(1 cup\)$/i)).toBeInTheDocument();
    });
  });

  it('deletes item when X button is clicked', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    await clickRemoveItem(user, 'apple');
    
    await waitFor(() => {
      expect(screen.queryByText(/^apple$/i)).not.toBeInTheDocument();
    });
  });

  it('shows removed items count after deletion', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    await clickRemoveItem(user, 'apple');
    
    await waitFor(() => {
      expect(screen.getByText(/1 item\(s\) removed/i)).toBeInTheDocument();
    });
  });

  it('sorts items alphabetically ascending by default', async () => {
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    const [firstItem, secondItem] = getRenderedItemNames();
    expect(firstItem).toBe('apple');
    expect(secondItem).toBe('butter');
  });

  it('sorts items alphabetically descending when Z-A selected', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    const sortSelect = screen.getByRole('combobox');
    await user.selectOptions(sortSelect, 'alpha-desc');
    
    const [firstItem] = getRenderedItemNames();
    expect(firstItem).toBe('cumin');
  });

  it('groups items by store section when By Store Section selected', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    const sortSelect = screen.getByRole('combobox');
    await user.selectOptions(sortSelect, 'by-section');
    
    expect(screen.getByText('Produce')).toBeInTheDocument();
    expect(screen.getByText('Dairy')).toBeInTheDocument();
    expect(screen.getByText('Meat & Seafood')).toBeInTheDocument();
    expect(screen.getByText('Spices & Seasonings')).toBeInTheDocument();
  });

  it('toggles item checked state when checkbox clicked', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/apple/i)).toBeInTheDocument();
    });
    
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).not.toBeChecked();
    
    await user.click(checkboxes[0]);
    expect(checkboxes[0]).toBeChecked();
    
    expect(screen.getByText(/1 of 4 items checked/i)).toBeInTheDocument();
  });

  it('updates item count correctly after deletions', async () => {
    const user = userEvent.setup();
    render(<GroceryList recipeIds={[1, 2]} />);
    
    await waitFor(() => {
      expect(screen.getByText(/0 of 4 items checked/i)).toBeInTheDocument();
    });
    
    await clickRemoveItem(user, 'apple');
    
    await waitFor(() => {
      expect(screen.getByText(/0 of 3 items checked/i)).toBeInTheDocument();
    });
  });
});
