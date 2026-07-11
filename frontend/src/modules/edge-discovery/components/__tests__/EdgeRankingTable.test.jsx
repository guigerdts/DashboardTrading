import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { EdgeRankingTable } from '../EdgeRankingTable';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockRankings = [
  {
    group_id: 'strat_trend_asset_eur',
    dimensions: { strategy: 'Trend Following', asset: 'EURUSD' },
    trade_ids: [1, 2, 3],
    trade_count: 3,
    expectancy: 125.5,
    net_pnl: 376.5,
    profit_factor: 2.1,
    confidence_interval: [50.0, 200.0],
    p_value: 0.023,
    fdr_adjusted_p_value: 0.045,
    stability_score: 0.88,
    edge_score: 0.72,
    confidence_level: 'high',
    failure_reasons: [],
  },
  {
    group_id: 'strat_reversion_asset_gbp',
    dimensions: { strategy: 'Mean Reversion', asset: 'GBPUSD' },
    trade_ids: [4, 5],
    trade_count: 2,
    expectancy: -30.0,
    net_pnl: -60.0,
    profit_factor: 0.7,
    confidence_interval: [-80.0, 20.0],
    p_value: 0.15,
    fdr_adjusted_p_value: 0.22,
    stability_score: 0.45,
    edge_score: 0.12,
    confidence_level: 'low',
    failure_reasons: ['p_value > 0.05'],
  },
];

const mockResponse = {
  snapshot_id: 'snap_001',
  generated_at: '2025-01-15T10:00:00Z',
  parameters: { min_observations: 5, bootstrap_resamples: 1000, fdr_alpha: 0.05, stability_threshold: 0.7, seed: null },
  trade_count: 5,
  rankings: mockRankings,
};

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ── Loading state ─────────────────────────────────────────────────────────

describe('EdgeRankingTable — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = renderWithRouter(
      <EdgeRankingTable
        data={undefined}
        isLoading={true}
        isError={false}
        error={null}
      />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('EdgeRankingTable — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    renderWithRouter(
      <EdgeRankingTable
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('API error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('API error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('EdgeRankingTable — empty state', () => {
  it('shows "No edges found" when rankings array is empty', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={{ rankings: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No edges found')).toBeInTheDocument();
  });

  it('shows "No edges found" when data is null', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={null}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No edges found')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('EdgeRankingTable — success state', () => {
  it('renders the edge count', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText(/Edge Rankings \(2\)/)).toBeInTheDocument();
  });

  it('renders all column headers', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Dimensions')).toBeInTheDocument();
    expect(screen.getByText('Edge Score')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('CI (95%)')).toBeInTheDocument();
    expect(screen.getByText('Stability')).toBeInTheDocument();
    expect(screen.getByText('Level')).toBeInTheDocument();
  });

  it('renders dimension values as row text', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Trend Following · EURUSD')).toBeInTheDocument();
    expect(screen.getByText('Mean Reversion · GBPUSD')).toBeInTheDocument();
  });

  it('renders confidence level badges', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('sorts by edge_score descending', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const rows = screen.getAllByRole('row');
    // Row 0 is header, row 1 = first item (edge_score 0.72), row 2 = second (edge_score 0.12)
    expect(rows[1]).toHaveTextContent('Trend Following · EURUSD');
    expect(rows[2]).toHaveTextContent('Mean Reversion · GBPUSD');
  });

  it('renders formatted expectancy with color', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('$125.50')).toBeInTheDocument();
    expect(screen.getByText('-$30.00')).toBeInTheDocument();
  });

  it('renders the toggle checkbox when onToggleInsufficient is provided', () => {
    const onToggle = vi.fn();
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
        showInsufficient={false}
        onToggleInsufficient={onToggle}
      />,
    );
    expect(screen.getByText('Show insufficient')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('does not render toggle when onToggleInsufficient is missing', () => {
    renderWithRouter(
      <EdgeRankingTable
        data={mockResponse}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText('Show insufficient')).not.toBeInTheDocument();
  });
});
