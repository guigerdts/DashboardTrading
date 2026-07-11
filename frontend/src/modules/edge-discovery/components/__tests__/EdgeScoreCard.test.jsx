import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EdgeScoreCard } from '../EdgeScoreCard';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockEdge = {
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
};

const mockData = {
  edge: mockEdge,
  trades: [
    { id: 1, strategy: 'Trend Following', setup: null, asset: 'EURUSD', direction: 'long', pnl: 150, tags: [], mistakes: [] },
    { id: 2, strategy: 'Trend Following', setup: null, asset: 'EURUSD', direction: 'long', pnl: -25, tags: [], mistakes: [] },
    { id: 3, strategy: 'Trend Following', setup: null, asset: 'EURUSD', direction: 'long', pnl: 251.5, tags: [], mistakes: [] },
  ],
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('EdgeScoreCard — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <EdgeScoreCard data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('EdgeScoreCard — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <EdgeScoreCard
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

describe('EdgeScoreCard — empty state', () => {
  it('renders "No edge data available" when data is null', () => {
    render(
      <EdgeScoreCard data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No edge data available')).toBeInTheDocument();
  });

  it('renders "No edge data available" when edge is missing', () => {
    render(
      <EdgeScoreCard data={{}} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No edge data available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('EdgeScoreCard — success state', () => {
  it('renders dimension badges', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText(/Trend Following/)).toBeInTheDocument();
    expect(screen.getByText(/EURUSD/)).toBeInTheDocument();
  });

  it('renders High stability indicator', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders expectancy formatted as currency', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('$125.50')).toBeInTheDocument();
  });

  it('renders p-value', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('0.02')).toBeInTheDocument();
  });

  it('renders confidence interval range', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('[$50.00, $200.00]')).toBeInTheDocument();
  });

  it('renders stability percentage', () => {
    render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('88%')).toBeInTheDocument();
  });

  it('applies green left border for high confidence', () => {
    const { container } = render(
      <EdgeScoreCard data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-green-500');
  });

  it('applies red left border for insufficient confidence', () => {
    const insufficient = {
      ...mockData,
      edge: { ...mockEdge, confidence_level: 'insufficient' },
    };
    const { container } = render(
      <EdgeScoreCard data={insufficient} isLoading={false} isError={false} error={null} />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-red-400');
  });
});
