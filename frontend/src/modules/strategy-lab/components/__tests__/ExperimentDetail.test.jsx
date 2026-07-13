import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExperimentDetail } from '../ExperimentDetail';

// ── Mocks ────────────────────────────────────────────────────────────────

const mockExperimentData = {
  experiment: {
    id: 1,
    name: 'Trend Following v2',
    hypothesis: 'Testing trend following with ATR-based stops on 4H',
    status: 'running',
    created_at: '2025-06-01T10:00:00Z',
  },
  runs: [
    {
      id: 101,
      status: 'completed',
      created_at: '2025-06-01T12:00:00Z',
      engine_version: 'v1.0.0',
      metrics_count: 15,
    },
    {
      id: 102,
      status: 'running',
      created_at: '2025-06-02T08:00:00Z',
      engine_version: 'v1.1.0',
      metrics_count: null,
    },
    {
      id: 103,
      status: 'failed',
      created_at: null,
      engine_version: null,
      metrics_count: null,
    },
  ],
};

vi.mock('../../hooks/useStrategyLab', () => ({
  useExperiment: vi.fn(),
  useCreateRun: vi.fn(),
  useStrategyVersions: vi.fn(),
}));

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

describe('ExperimentDetail — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({ data: undefined, isLoading: true, isError: false, error: null });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: undefined, isLoading: false });

    const { container } = renderWithProviders(<ExperimentDetail experimentId={1} />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ──────────────────────────────────────────────────────────

describe('ExperimentDetail — error state', () => {
  it('renders ErrorFallback with message', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    const refetch = vi.fn();
    useExperiment.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Experiment not found'),
      refetch,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: undefined, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={999} />);
    expect(screen.getByText('Experiment not found')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ──────────────────────────────────────────────────────────

describe('ExperimentDetail — empty state', () => {
  it('shows "Experiment not found" when experiment is null', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: { experiment: null, runs: [] },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: undefined, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={999} />);
    expect(screen.getByText('Experiment not found')).toBeInTheDocument();
  });

  it('shows "No runs yet" when runs array is empty', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: { experiment: { id: 1, name: 'Test', status: 'draft' }, runs: [] },
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: undefined, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(screen.getByText('No runs yet')).toBeInTheDocument();
  });
});

// ── Success state ────────────────────────────────────────────────────────

describe('ExperimentDetail — success state', () => {
  it('renders experiment name and status', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(screen.getByText('Trend Following v2')).toBeInTheDocument();
    // "Running" appears in both experiment status and runs table — use getAllByText
    const runningElements = screen.getAllByText('Running');
    expect(runningElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders hypothesis', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(
      screen.getByText('Testing trend following with ATR-based stops on 4H'),
    ).toBeInTheDocument();
  });

  it('renders runs count', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(screen.getByText(/Runs \(3\)/)).toBeInTheDocument();
  });

  it('renders run statuses', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('renders "New Run" button', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    expect(screen.getByText('New Run')).toBeInTheDocument();
  });

  it('opens new run form when "New Run" is clicked', async () => {
    const { useExperiment, useCreateRun, useStrategyVersions } = await import('../../hooks/useStrategyLab');
    useExperiment.mockReturnValue({
      data: mockExperimentData,
      isLoading: false,
      isError: false,
      error: null,
    });
    useCreateRun.mockReturnValue({ mutate: vi.fn(), isPending: false, isError: false, error: null });
    useStrategyVersions.mockReturnValue({ data: { versions: [{ id: 1, label: 'v1.0.0' }] }, isLoading: false });

    renderWithProviders(<ExperimentDetail experimentId={1} />);
    fireEvent.click(screen.getByText('New Run'));
    expect(screen.getByLabelText('Strategy Version')).toBeInTheDocument();
    expect(screen.getByText('Start Run')).toBeInTheDocument();
  });
});
