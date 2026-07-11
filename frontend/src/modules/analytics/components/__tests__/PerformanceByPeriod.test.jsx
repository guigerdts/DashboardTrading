import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PerformanceByPeriod } from '../PerformanceByPeriod';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockRecords = [
  {
    period: '2024-01',
    trade_count: 15,
    net_pnl: 1250.5,
    gross_profit: 5000,
    gross_loss: -3750,
    win_rate: 0.6,
    profit_factor: 1.33,
    expectancy: 83.37,
    avg_r_multiple: 1.25,
  },
  {
    period: '2024-02',
    trade_count: 12,
    net_pnl: -500,
    gross_profit: 2000,
    gross_loss: -2500,
    win_rate: 0.5,
    profit_factor: 0.8,
    expectancy: -41.67,
    avg_r_multiple: 0.9,
  },
];

const mockData = {
  records: mockRecords,
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('PerformanceByPeriod — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <PerformanceByPeriod data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('PerformanceByPeriod — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <PerformanceByPeriod
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Period error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Period error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <PerformanceByPeriod
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load performance by period')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('PerformanceByPeriod — empty state', () => {
  it('shows empty message when records is empty array', () => {
    render(
      <PerformanceByPeriod
        data={{ records: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No performance data available')).toBeInTheDocument();
  });

  it('shows empty message when records is undefined', () => {
    render(
      <PerformanceByPeriod
        data={{ records: undefined }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No performance data available')).toBeInTheDocument();
  });

  it('shows empty message when data is null', () => {
    render(
      <PerformanceByPeriod data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No performance data available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('PerformanceByPeriod — success state', () => {
  it('renders the title', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Performance by Period')).toBeInTheDocument();
  });

  it('renders period toggle buttons', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Monthly')).toBeInTheDocument();
    expect(screen.getByText('Quarterly')).toBeInTheDocument();
    expect(screen.getByText('Yearly')).toBeInTheDocument();
  });

  it('renders all column headers', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Period')).toBeInTheDocument();
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Avg R')).toBeInTheDocument();
  });

  it('renders period records', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('2024-01')).toBeInTheDocument();
    expect(screen.getByText('2024-02')).toBeInTheDocument();
  });

  it('formats Net P&L as currency for positive values', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('$1,250.50')).toBeInTheDocument();
  });

  it('formats Net P&L as currency for negative values', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('-$500.00')).toBeInTheDocument();
  });

  it('formats Win Rate as percentage', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('60.00%')).toBeInTheDocument();
    expect(screen.getByText('50.00%')).toBeInTheDocument();
  });

  it('formats Profit Factor as ratio', () => {
    render(
      <PerformanceByPeriod data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('1.3300')).toBeInTheDocument();
  });
});
