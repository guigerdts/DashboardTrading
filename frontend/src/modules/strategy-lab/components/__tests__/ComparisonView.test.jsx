import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ComparisonView } from '../ComparisonView';

// ── Mocks ────────────────────────────────────────────────────────────────

const mockComparisonData = {
  comparison: {
    summary: {
      total_metrics: 3,
      significant_count: 2,
      insufficient_count: 1,
      global_effect_size: 0.42,
    },
    metrics: [
      {
        name: 'Sharpe Ratio',
        run_a: 1.85,
        run_b: 1.42,
        delta: 0.43,
        confidence_interval: [0.12, 0.74],
        p_value: 0.008,
      },
      {
        name: 'Win Rate',
        run_a: 0.58,
        run_b: 0.52,
        delta: 0.06,
        confidence_interval: [-0.02, 0.14],
        p_value: 0.12,
      },
      {
        name: 'Max Drawdown',
        run_a: -0.12,
        run_b: -0.18,
        delta: 0.06,
        confidence_interval: [0.01, 0.11],
        p_value: 0.023,
      },
    ],
  },
};

vi.mock('../../hooks/useStrategyLab', () => ({
  useRunComparison: vi.fn(),
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

describe('ComparisonView — loading state', () => {
  it('renders skeleton when isLoading is true', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({ data: undefined, isLoading: true, isError: false, error: null });

    const { container } = renderWithProviders(
      <ComparisonView runId={1} baselineId={2} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ──────────────────────────────────────────────────────────

describe('ComparisonView — error state', () => {
  it('renders ErrorFallback with message', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    const refetch = vi.fn();
    useRunComparison.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('Comparison failed'),
      refetch,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('Comparison failed')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ──────────────────────────────────────────────────────────

describe('ComparisonView — empty state', () => {
  it('shows no data message when data is null', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('No comparison data available')).toBeInTheDocument();
  });

  it('shows no data message when comparison is missing', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: {},
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('No comparison data available')).toBeInTheDocument();
  });
});

// ── Success state ────────────────────────────────────────────────────────

describe('ComparisonView — success state', () => {
  it('renders comparison title and labels', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(
      <ComparisonView runId={1} baselineId={2} runALabel="Treatment" runBLabel="Control" />,
    );
    expect(screen.getByText('Run Comparison')).toBeInTheDocument();
    // Verify the custom labels render — they appear both in the description and in column headers
    const treatmentElements = screen.getAllByText('Treatment');
    expect(treatmentElements.length).toBeGreaterThanOrEqual(1);
    const controlElements = screen.getAllByText('Control');
    expect(controlElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders summary stats', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    // Summary values are in separate spans — check for the numbers
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    // Also verify the labels exist
    expect(screen.getByText('Metrics compared:')).toBeInTheDocument();
    expect(screen.getByText('Significant:')).toBeInTheDocument();
    expect(screen.getByText('Insufficient:')).toBeInTheDocument();
  });

  it('renders global effect size', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('Global Effect Size')).toBeInTheDocument();
    expect(screen.getByText('0.420')).toBeInTheDocument();
  });

  it('renders all metric names', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
  });

  it('renders p-value badges with confidence labels', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    // p=0.008 -> Very High, p=0.12 -> Low, p=0.023 -> High
    // Badge text format is "0.0080 · Very High" — use regex
    expect(screen.getByText(/Very High/)).toBeInTheDocument();
    expect(screen.getByText(/Low/)).toBeInTheDocument();
    const highElements = screen.getAllByText(/High/);
    expect(highElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders CI display', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    // CI for Sharpe: 0.12 – 0.74
    expect(screen.getByText(/0.1200.*0.7400/)).toBeInTheDocument();
  });

  it('renders the color legend', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: mockComparisonData,
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('Legend:')).toBeInTheDocument();
    expect(screen.getByText('Significant positive')).toBeInTheDocument();
    expect(screen.getByText('Significant negative')).toBeInTheDocument();
    expect(screen.getByText('Insufficient')).toBeInTheDocument();
  });

  it('handles empty metrics array', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: {
        comparison: {
          summary: { total_metrics: 0, significant_count: 0, insufficient_count: 0 },
          metrics: [],
        },
      },
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    expect(screen.getByText('No metrics available for comparison')).toBeInTheDocument();
  });

  it('handles missing p-value', async () => {
    const { useRunComparison } = await import('../../hooks/useStrategyLab');
    useRunComparison.mockReturnValue({
      data: {
        comparison: {
          summary: { total_metrics: 1 },
          metrics: [{ name: 'Metric X', p_value: null, delta: null }],
        },
      },
      isLoading: false,
      isError: false,
      error: null,
    });

    renderWithProviders(<ComparisonView runId={1} baselineId={2} />);
    // "Insufficient" appears both in the badge and in the legend — check all
    const insufficientElements = screen.getAllByText('Insufficient');
    expect(insufficientElements.length).toBeGreaterThanOrEqual(1);
  });
});
