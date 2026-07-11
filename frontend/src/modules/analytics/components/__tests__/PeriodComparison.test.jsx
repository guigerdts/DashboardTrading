import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PeriodComparison } from '../PeriodComparison';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockPeriodA = {
  period: 'period_a',
  trade_count: 50,
  net_pnl: 2500,
  gross_profit: 5000,
  gross_loss: -2500,
  win_rate: 0.6,
  profit_factor: 2.0,
  expectancy: 50.0,
  avg_r_multiple: 1.5,
};

const mockPeriodB = {
  period: 'period_b',
  trade_count: 40,
  net_pnl: 1000,
  gross_profit: 3000,
  gross_loss: -2000,
  win_rate: 0.55,
  profit_factor: 1.5,
  expectancy: 25.0,
  avg_r_multiple: 1.2,
};

const mockDelta = {
  period: 'delta',
  trade_count: 10,
  net_pnl: 1500,
  gross_profit: 2000,
  gross_loss: -500,
  win_rate: 0.05,
  profit_factor: 0.5,
  expectancy: 25.0,
  avg_r_multiple: 0.3,
};

const mockDeltaPercent = {
  period: 'delta_pct',
  trade_count: 20,
  net_pnl: 60,
  gross_profit: 40,
  gross_loss: 20,
  win_rate: 8.33,
  profit_factor: 25,
  expectancy: 50,
  avg_r_multiple: 20,
};

const mockData = {
  period_a: mockPeriodA,
  period_b: mockPeriodB,
  delta: mockDelta,
  delta_percent: mockDeltaPercent,
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('PeriodComparison — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <PeriodComparison data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('PeriodComparison — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <PeriodComparison
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Compare error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Compare error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <PeriodComparison
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load period comparison')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('PeriodComparison — empty state', () => {
  it('shows empty message when data is null', () => {
    render(
      <PeriodComparison data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No comparison data available')).toBeInTheDocument();
  });

  it('shows empty message when period_a is missing', () => {
    render(
      <PeriodComparison
        data={{ period_a: undefined, period_b: mockPeriodB, delta: mockDelta, delta_percent: mockDeltaPercent }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No comparison data available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('PeriodComparison — success state', () => {
  it('renders the title', () => {
    render(
      <PeriodComparison data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Period Comparison')).toBeInTheDocument();
  });

  it('renders all column headers', () => {
    render(
      <PeriodComparison data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Metric')).toBeInTheDocument();
    expect(screen.getByText('Period A')).toBeInTheDocument();
    expect(screen.getByText('Period B')).toBeInTheDocument();
    expect(screen.getByText('Delta')).toBeInTheDocument();
    expect(screen.getByText('Delta %')).toBeInTheDocument();
  });

  it('renders metric labels', () => {
    render(
      <PeriodComparison data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Gross Profit')).toBeInTheDocument();
    expect(screen.getByText('Gross Loss')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Avg R')).toBeInTheDocument();
  });

  it('renders Period A values', () => {
    render(
      <PeriodComparison data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    expect(screen.getByText('$1,000.00')).toBeInTheDocument(); // Period B
    expect(screen.getByText('$1,500.00')).toBeInTheDocument(); // Delta
  });

  it('renders Delta % values', () => {
    render(
      <PeriodComparison data={mockData} isLoading={false} isError={false} error={null} />,
    );
    // 60.00% appears as both win_rate for Period A and delta_percent for net_pnl
    const pctValues = screen.getAllByText('60.00%');
    expect(pctValues.length).toBe(2);
  });

  it('shows — for null profit_factor in delta', () => {
    const nullDelta = {
      ...mockData,
      delta: {
        ...mockData.delta,
        profit_factor: null,
        avg_r_multiple: null,
      },
    };
    render(
      <PeriodComparison data={nullDelta} isLoading={false} isError={false} error={null} />,
    );
    // null values should render em-dash
    const dashes = screen.getAllByText('\u2014');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });
});
