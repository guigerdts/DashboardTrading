import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function renderWithWrapper(ui) {
  return render(ui, { wrapper: createWrapper() });
}

// Mock catalog hooks
vi.mock('../hooks/useCatalog', () => ({
  useCatalogList: vi.fn(),
}));

// Mock trade context hooks
vi.mock('../hooks/useTradeContext', () => ({
  useUpdateTradeStrategy: vi.fn(),
  useUpdateTradeSetup: vi.fn(),
  useSyncTradeTags: vi.fn(),
  useSyncTradeMistakes: vi.fn(),
}));

import { useCatalogList } from '../hooks/useCatalog';
import { useUpdateTradeStrategy, useUpdateTradeSetup, useSyncTradeTags, useSyncTradeMistakes } from '../hooks/useTradeContext';
import { ContextSection } from '../../trade-review/components/ContextSection';

const mockStrategies = [
  { id: 1, name: 'Trend Following', is_active: true },
  { id: 2, name: 'Mean Reversion', is_active: true },
];

const mockSetups = [
  { id: 1, name: 'Breakout', is_active: true },
  { id: 2, name: 'Pullback', is_active: true },
];

const mockTags = [
  { id: 1, name: 'EURUSD', category: 'Pair' },
  { id: 2, name: 'Momentum', category: 'Style' },
  { id: 3, name: 'Failed', category: 'Outcome' },
];

const mockMistakes = [
  { id: 1, name: 'FOMO Entry', is_active: true },
  { id: 2, name: 'No Stop Loss', is_active: true },
];

const mockTradeData = {
  id: 42,
  strategy_id: null,
  strategy_name: null,
  setup_id: null,
  setup_name: null,
  tags: [],
  mistakes: [],
};

function createMutationMock() {
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

describe('ContextSection — F4: Context selectors call correct mutation', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    useCatalogList.mockImplementation((entity) => {
      const map = {
        strategies: mockStrategies,
        setups: mockSetups,
        tags: mockTags,
        mistakes: mockMistakes,
      };
      return { data: map[entity] || [], isLoading: false };
    });

    useUpdateTradeStrategy.mockReturnValue(createMutationMock());
    useUpdateTradeSetup.mockReturnValue(createMutationMock());
    useSyncTradeTags.mockReturnValue(createMutationMock());
    useSyncTradeMistakes.mockReturnValue(createMutationMock());
  });

  it('renders strategy and setup dropdowns', () => {
    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    expect(screen.getByText('Strategy')).toBeInTheDocument();
    expect(screen.getByText('Setup')).toBeInTheDocument();
    expect(screen.getByText('Tags')).toBeInTheDocument();
    expect(screen.getByText('Mistakes')).toBeInTheDocument();

    expect(screen.getByText('Select strategy...')).toBeInTheDocument();
    expect(screen.getByText('Select setup...')).toBeInTheDocument();
  });

  it('calls update strategy mutation when strategy is changed and saved', async () => {
    const mockUpdateStrategy = vi.fn().mockResolvedValue({});
    useUpdateTradeStrategy.mockReturnValue({
      ...createMutationMock(),
      mutateAsync: mockUpdateStrategy,
    });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    // Select a strategy from dropdown
    const strategySelect = screen.getByText('Select strategy...').closest('select')
      || screen.getByRole('combobox');
    await userEvent.selectOptions(strategySelect, '1');

    // Click save
    await userEvent.click(screen.getByText('Save Context'));

    await waitFor(() => {
      expect(mockUpdateStrategy).toHaveBeenCalledWith(1);
    });
  });

  it('calls sync tags mutation when tags are changed and saved', async () => {
    const mockSyncTags = vi.fn().mockResolvedValue({});
    useSyncTradeTags.mockReturnValue({
      ...createMutationMock(),
      mutateAsync: mockSyncTags,
    });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    // Open tags multi-select
    const tagsTrigger = screen.getByText('Select tags...');
    await userEvent.click(tagsTrigger);

    // Select EURUSD tag
    const checkbox = screen.getByText('EURUSD');
    await userEvent.click(checkbox);

    // Click save
    await userEvent.click(screen.getByText('Save Context'));

    await waitFor(() => {
      // Tags should be synced with the selected tag ID
      // The multi-select is a custom dropdown, need to check mutation was called with [1]
      expect(mockSyncTags).toHaveBeenCalledWith([1]);
    });
  });

  it('calls setup update mutation when setup is changed and saved', async () => {
    const mockUpdateSetup = vi.fn().mockResolvedValue({});
    useUpdateTradeSetup.mockReturnValue({
      ...createMutationMock(),
      mutateAsync: mockUpdateSetup,
    });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    // Select a setup
    const setupSelect = screen.getByText('Select setup...').closest('select')
      || screen.getAllByRole('combobox')[1];
    await userEvent.selectOptions(setupSelect, '1');

    // Save
    await userEvent.click(screen.getByText('Save Context'));

    await waitFor(() => {
      expect(mockUpdateSetup).toHaveBeenCalledWith(1);
    });
  });

  it('does not call mutations when there are no changes', async () => {
    const mockUpdateStrategy = vi.fn().mockResolvedValue({});
    const mockUpdateSetup = vi.fn().mockResolvedValue({});
    const mockSyncTags = vi.fn().mockResolvedValue({});
    const mockSyncMistakes = vi.fn().mockResolvedValue({});

    useUpdateTradeStrategy.mockReturnValue({ ...createMutationMock(), mutateAsync: mockUpdateStrategy });
    useUpdateTradeSetup.mockReturnValue({ ...createMutationMock(), mutateAsync: mockUpdateSetup });
    useSyncTradeTags.mockReturnValue({ ...createMutationMock(), mutateAsync: mockSyncTags });
    useSyncTradeMistakes.mockReturnValue({ ...createMutationMock(), mutateAsync: mockSyncMistakes });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    // Save button should be disabled since no changes
    expect(screen.getByText('Save Context')).toBeDisabled();
  });

  it('shows error message when mutation fails', async () => {
    useUpdateTradeStrategy.mockReturnValue({
      ...createMutationMock(),
      mutateAsync: vi.fn().mockRejectedValue({
        data: { detail: 'Archived strategy cannot be assigned to new trades' },
      }),
    });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    const strategySelect = screen.getByText('Select strategy...').closest('select')
      || screen.getByRole('combobox');
    await userEvent.selectOptions(strategySelect, '1');

    await userEvent.click(screen.getByText('Save Context'));

    await waitFor(() => {
      expect(screen.getByText(/archived strategy cannot be assigned/i)).toBeInTheDocument();
    });
  });

  it('shows loading state when trade data is loading', () => {
    const { container } = renderWithWrapper(<ContextSection data={null} isLoading={true} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('calls sync mistakes mutation when mistakes are changed and saved', async () => {
    const mockSyncMistakes = vi.fn().mockResolvedValue({});
    useSyncTradeMistakes.mockReturnValue({
      ...createMutationMock(),
      mutateAsync: mockSyncMistakes,
    });

    renderWithWrapper(<ContextSection data={mockTradeData} isLoading={false} />);

    // Open mistakes multi-select
    const mistakesTrigger = screen.getByText('Select mistakes...');
    await userEvent.click(mistakesTrigger);

    // Select FOMO Entry
    const checkbox = screen.getByText('FOMO Entry');
    await userEvent.click(checkbox);

    // Save
    await userEvent.click(screen.getByText('Save Context'));

    await waitFor(() => {
      expect(mockSyncMistakes).toHaveBeenCalledWith([{ id: 1 }]);
    });
  });
});
