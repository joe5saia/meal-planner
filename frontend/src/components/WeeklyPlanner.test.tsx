import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WeeklyPlanner, type WeekCount } from './WeeklyPlanner';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    mealPlans: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    recipes: {
      getBox: vi.fn(),
    },
  },
}));

describe('WeeklyPlanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.mealPlans.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (api.recipes.getBox as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it('renders with 7 day cells when weeksToShow is 1', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={1}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const dayCheckboxes = screen.getAllByRole('checkbox');
    expect(dayCheckboxes).toHaveLength(7);
  });

  it('renders with 14 day cells when weeksToShow is 2', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={2}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const dayCheckboxes = screen.getAllByRole('checkbox');
    expect(dayCheckboxes).toHaveLength(14);
  });

  it('renders with 21 day cells when weeksToShow is 3', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={3}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const dayCheckboxes = screen.getAllByRole('checkbox');
    expect(dayCheckboxes).toHaveLength(21);
  });

  it('renders with 28 day cells when weeksToShow is 4', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={4}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const dayCheckboxes = screen.getAllByRole('checkbox');
    expect(dayCheckboxes).toHaveLength(28);
  });

  it('calls onWeeksToShowChange when 2W button is clicked', async () => {
    const user = userEvent.setup();
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={1}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const twoWeekButton = screen.getByRole('button', { name: '2W' });
    await user.click(twoWeekButton);

    expect(onWeeksToShowChange).toHaveBeenCalledWith(2);
  });

  it('calls onWeeksToShowChange when 3W button is clicked', async () => {
    const user = userEvent.setup();
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={1}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const threeWeekButton = screen.getByRole('button', { name: '3W' });
    await user.click(threeWeekButton);

    expect(onWeeksToShowChange).toHaveBeenCalledWith(3);
  });

  it('calls onWeeksToShowChange when 4W button is clicked', async () => {
    const user = userEvent.setup();
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={1}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const fourWeekButton = screen.getByRole('button', { name: '4W' });
    await user.click(fourWeekButton);

    expect(onWeeksToShowChange).toHaveBeenCalledWith(4);
  });

  it('highlights the current weeksToShow button', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={2}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    const twoWeekButton = screen.getByRole('button', { name: '2W' });
    const oneWeekButton = screen.getByRole('button', { name: '1W' });

    expect(twoWeekButton.className).toContain('bg-emerald-600');
    expect(oneWeekButton.className).not.toContain('bg-emerald-600');
  });

  it('fetches data for correct date range based on weeksToShow', async () => {
    const onWeeksToShowChange = vi.fn();
    render(
      <WeeklyPlanner
        weeksToShow={2}
        onWeeksToShowChange={onWeeksToShowChange}
      />
    );

    await waitFor(() => {
      expect(api.mealPlans.list).toHaveBeenCalled();
    });

    const [startDate, endDate] = (api.mealPlans.list as ReturnType<typeof vi.fn>).mock.calls[0];
    
    const start = new Date(startDate);
    const end = new Date(endDate);
    const daysDiff = Math.round((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
    
    expect(daysDiff).toBe(13);
  });
});
