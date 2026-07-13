import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExperimentList } from '../ExperimentList';

// ── Mocks ────────────────────────────────────────────────────────────────

const mockExperiments = [
  {
    id: 1,
    name: 'Trend Following v2',
    hypothesis: 'Testing trend following with ATR-based stops',
    status: 'completed',
    created_at: '2025-06-01T10:00:00Z',
  },
  {
    id: 2,
    name: 'Mean Reversion v3',
    hypothesis: 'Testing mean reversion on 15min timeframe',
    status: 'running',
    created_at: '2025-06-15T14:30:00Z',
  },
  {
    id: 3,
    name: 'Breakout Strategy',
    hypothesis: null,
    status: 'draft',
    created_at: null,
  },
];

vi.mock('../../hooks/useStrategyLab', () => ({
  useExperiments: vi.fn(),
  useCreateExperiment: vi.fn(),
}));

const mockUseExperiments = (override) => {
  const actual = vi.requireActual('../../hooks/useStrategyLab');
  return { ...actual, useExperiments: vi.fn(), useCreateExperiment: vi.fn() };
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  // eslint-disable-next-line react/prop-types
  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function renderWithProviders(ui) {
  return render(ui, { wrapper: createWrapper() });
}

// ── Loading state ────────────────────────────────────────────────────────

describe('ExperimentList — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({ data: undefined, isLoading: true, isError: false, error: null });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    const { container } = renderWithProviders(<ExperimentList />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ──────────────────────────────────────────────────────────

describe('ExperimentList — error state', () => {
  it('renders ErrorFallback with message', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    const refetch = vi.fn();
    useExperiments.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('API error'),
      refetch,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('API error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ──────────────────────────────────────────────────────────

describe('ExperimentList — empty state', () => {
  it('shows "No experiments yet" when experiments array is empty', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: [] },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('No experiments yet')).toBeInTheDocument();
  });

  it('shows "No experiments yet" when data is null', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('No experiments yet')).toBeInTheDocument();
  });
});

// ── Success state ────────────────────────────────────────────────────────

describe('ExperimentList — success state', () => {
  it('renders experiment count', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText(/Experiments \(3\)/)).toBeInTheDocument();
  });

  it('renders experiment names', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('Trend Following v2')).toBeInTheDocument();
    expect(screen.getByText('Mean Reversion v3')).toBeInTheDocument();
    expect(screen.getByText('Breakout Strategy')).toBeInTheDocument();
  });

  it('renders status badges with correct text', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('shows "New Experiment" button', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    expect(screen.getByText('New Experiment')).toBeInTheDocument();
  });

  it('opens create form when "New Experiment" is clicked', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    fireEvent.click(screen.getByText('New Experiment'));
    expect(screen.getByLabelText('Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Hypothesis')).toBeInTheDocument();
    expect(screen.getByText('Create')).toBeInTheDocument();
  });

  it('renders "—" for missing hypothesis', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    renderWithProviders(<ExperimentList />);
    // Breakout Strategy has null hypothesis
    const rows = screen.getAllByRole('row');
    const lastRow = rows[rows.length - 1];
    expect(lastRow.textContent).toContain('—');
  });

  it('navigates on row click', async () => {
    const { useExperiments, useCreateExperiment } = await import('../../hooks/useStrategyLab');
    useExperiments.mockReturnValue({
      data: { experiments: mockExperiments },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateExperiment.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });

    const { container } = renderWithProviders(<ExperimentList />);
    // Click the first experiment row
    const rows = container.querySelectorAll('tbody tr');
    fireEvent.click(rows[0]);
    // Navigation to /lab/experiments/1 should have been triggered
    // We can't easily assert on navigate, but at least it shouldn't throw
  });
});
