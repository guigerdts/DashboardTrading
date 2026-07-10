import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// ── F1: Admin list renders catalog elements ──────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function renderWithWrapper(ui) {
  return render(ui, { wrapper: createWrapper() });
}

const mockItems = [
  { id: 1, name: 'Trend Following', description: 'Follow the trend', is_active: true },
  { id: 2, name: 'Mean Reversion', description: 'Bet against extremes', is_active: true },
  { id: 3, name: 'Scalping', description: 'Quick small profits', is_active: false },
];

function createMockListResult(data = mockItems) {
  return { data, isLoading: false, isError: false, error: null, refetch: vi.fn() };
}

function createMockMutation() {
  return {
    mutate: vi.fn(),
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
    isSuccess: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  };
}

// Mock the hooks so we control data without API calls
vi.mock('../hooks/useCatalog', () => ({
  useCatalogList: vi.fn(),
  useCatalogCreate: vi.fn(),
  useCatalogUpdate: vi.fn(),
  useCatalogArchive: vi.fn(),
}));

import { useCatalogList, useCatalogCreate, useCatalogUpdate, useCatalogArchive } from '../hooks/useCatalog';
import StrategiesPage from '../strategies/StrategiesPage';

describe('CatalogAdmin — F1: Admin list renders catalog elements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCatalogList.mockReturnValue(createMockListResult());
    useCatalogCreate.mockReturnValue(createMockMutation());
    useCatalogUpdate.mockReturnValue(createMockMutation());
    useCatalogArchive.mockReturnValue(createMockMutation());
  });

  it('renders the page title and description', () => {
    renderWithWrapper(<StrategiesPage />);
    expect(screen.getByText('Strategies')).toBeInTheDocument();
    expect(screen.getByText(/manage your trading strategies/i)).toBeInTheDocument();
  });

  it('renders table with active catalog items (archived items hidden by default)', () => {
    renderWithWrapper(<StrategiesPage />);
    expect(screen.getByText('Trend Following')).toBeInTheDocument();
    expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
    // Scalping has is_active=false so it's hidden by default
    expect(screen.queryByText('Scalping')).not.toBeInTheDocument();
  });

  it('shows column headers for name and description', () => {
    renderWithWrapper(<StrategiesPage />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Actions')).toBeInTheDocument();
  });

  it('shows archived items with reduced opacity when toggle is on', async () => {
    renderWithWrapper(<StrategiesPage />);
    // Initially only 2 active items visible (Scalping is archived)
    expect(screen.getByText(/total/)).toHaveTextContent('3 total');
    expect(screen.getByText(/2 active/)).toBeInTheDocument();

    // Toggle show archived
    const checkbox = screen.getByText('Show archived items');
    await userEvent.click(checkbox);

    // Now all 3 should be in active count
    expect(screen.getByText(/3 total/)).toBeInTheDocument();
  });

  it('shows loading skeleton while loading', () => {
    useCatalogList.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = renderWithWrapper(<StrategiesPage />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows empty state when no items exist', () => {
    useCatalogList.mockReturnValue(createMockListResult([]));
    renderWithWrapper(<StrategiesPage />);
    expect(screen.getByText(/no strategies/i)).toBeInTheDocument();
  });

  it('shows error fallback on query error', () => {
    useCatalogList.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Network error'),
      refetch: vi.fn(),
    });
    renderWithWrapper(<StrategiesPage />);
    expect(screen.getByText('Network error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── F2: Create/edit form submits correct payload ─────────────────────────

describe('CatalogAdmin — F2: Create/edit form submits correct payload', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCatalogList.mockReturnValue(createMockListResult());
    useCatalogCreate.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: vi.fn().mockResolvedValue({ id: 4, name: 'Breakout', description: 'Price breaks key level' }),
    });
    useCatalogUpdate.mockReturnValue(createMockMutation());
    useCatalogArchive.mockReturnValue(createMockMutation());
  });

  it('opens create form and submits correct payload', async () => {
    const mockCreate = vi.fn().mockResolvedValue({ id: 4, name: 'Breakout', description: 'Price breaks key level' });
    useCatalogCreate.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: mockCreate,
    });

    renderWithWrapper(<StrategiesPage />);

    // Click create button
    await userEvent.click(screen.getByText('+ New strategy'));

    // Form should be visible
    expect(screen.getByText('Create strategy')).toBeInTheDocument();

    // Fill in fields
    await userEvent.type(screen.getByPlaceholderText(/enter strategy name/i), 'Breakout');
    const descInput = screen.getByPlaceholderText(/optional description/i);
    await userEvent.type(descInput, 'Price breaks key level');

    // Submit
    await userEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        name: 'Breakout',
        description: 'Price breaks key level',
      });
    });
  });

  it('opens edit form with pre-filled data and submits update', async () => {
    const mockUpdate = vi.fn().mockResolvedValue({ id: 1, name: 'Trend Following Updated', description: 'Updated' });
    useCatalogUpdate.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: mockUpdate,
    });

    renderWithWrapper(<StrategiesPage />);

    // Click edit button on first item
    const editButtons = screen.getAllByText('Edit');
    await userEvent.click(editButtons[0]);

    // Form should show "Edit strategy"
    expect(screen.getByText('Edit strategy')).toBeInTheDocument();

    // Fields should be pre-filled
    const nameInput = screen.getByDisplayValue('Trend Following');
    expect(nameInput).toBeInTheDocument();

    // Modify name
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Trend Following Updated');

    // Submit update
    await userEvent.click(screen.getByText('Update'));

    await waitFor(() => {
      // Strategy entities do NOT include category/color — those are tag-only fields
      expect(mockUpdate).toHaveBeenCalledWith({
        id: 1,
        name: 'Trend Following Updated',
        description: 'Follow the trend',
      });
    });
  });

  it('cancels the form and resets state', async () => {
    renderWithWrapper(<StrategiesPage />);

    // Open create form
    await userEvent.click(screen.getByText('+ New strategy'));
    expect(screen.getByText('Create strategy')).toBeInTheDocument();

    // Type something
    await userEvent.type(screen.getByPlaceholderText(/enter strategy name/i), 'test');

    // Click Cancel
    await userEvent.click(screen.getByText('Cancel'));

    // Form should be hidden
    expect(screen.queryByText('Create strategy')).not.toBeInTheDocument();
  });

  it('shows error message on failed submission', async () => {
    useCatalogCreate.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: vi.fn().mockRejectedValue({
        data: { detail: 'Strategy with this name already exists' },
        message: 'API Error: 409',
      }),
    });

    renderWithWrapper(<StrategiesPage />);

    await userEvent.click(screen.getByText('+ New strategy'));
    await userEvent.type(screen.getByPlaceholderText(/enter strategy name/i), 'Duplicate');
    await userEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(screen.getByText('Strategy with this name already exists')).toBeInTheDocument();
    });
  });
});

// ── F3: Archive removes from list ────────────────────────────────────────

describe('CatalogAdmin — F3: Archive removes from active list', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useCatalogList.mockReturnValue(createMockListResult());
    useCatalogCreate.mockReturnValue(createMockMutation());
    useCatalogUpdate.mockReturnValue(createMockMutation());
    useCatalogArchive.mockReturnValue(createMockMutation());
  });

  it('calls archive mutation when archive button is clicked', async () => {
    const mockArchive = vi.fn().mockResolvedValue(undefined);
    useCatalogArchive.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: mockArchive,
    });

    renderWithWrapper(<StrategiesPage />);

    // Click Archive on first item
    const archiveButtons = screen.getAllByText('Archive');
    await userEvent.click(archiveButtons[0]);

    await waitFor(() => {
      expect(mockArchive).toHaveBeenCalledWith(1);
    });
  });

  it('shows Restore button for archived items when showArchived is toggled', async () => {
    useCatalogList.mockReturnValue(createMockListResult([
      { id: 3, name: 'Scalping', description: 'Quick small profits', is_active: false },
    ]));

    renderWithWrapper(<StrategiesPage />);

    // Toggle show archived
    await userEvent.click(screen.getByText('Show archived items'));

    // Archived item should show "Restore" instead of "Archive"
    expect(screen.getByText('Scalping')).toBeInTheDocument();
    expect(screen.getByText('Restore')).toBeInTheDocument();
  });

  it('shows error when archive fails', async () => {
    useCatalogArchive.mockReturnValue({
      ...createMockMutation(),
      mutateAsync: vi.fn().mockRejectedValue(new Error('Failed to archive')),
    });

    renderWithWrapper(<StrategiesPage />);

    const archiveButtons = screen.getAllByText('Archive');
    await userEvent.click(archiveButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Failed to archive')).toBeInTheDocument();
    });
  });
});
