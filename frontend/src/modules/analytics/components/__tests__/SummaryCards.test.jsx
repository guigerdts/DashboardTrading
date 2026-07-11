import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SummaryCards } from '../SummaryCards';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockData = {
  performance: {
    net_pnl: 1250.5,
    win_rate: 0.65,
    profit_factor: 1.85,
    expectancy: 45.2,
    avg_r_multiple: 1.35,
    gross_profit: 5000,
    gross_loss: -3750,
  },
  risk: {
    max_drawdown: -0.12,
  },
  total_trades_all: 342,
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('SummaryCards — loading state', () => {
  it('renders 7 skeleton containers when isLoading is true', () => {
    const { container } = render(
      <SummaryCards data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBe(14);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('SummaryCards — error state', () => {
  it('renders ErrorFallback with message and retry button', () => {
    const onRetry = vi.fn();
    render(
      <SummaryCards
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

  it('renders default message when error has no message', () => {
    render(
      <SummaryCards
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load summary')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('SummaryCards — empty state', () => {
  it('renders 7 KPI titles when data is null', () => {
    render(
      <SummaryCards data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
    expect(screen.getByText('Avg R')).toBeInTheDocument();
  });

  it('renders 7 KPI titles when data is undefined', () => {
    render(
      <SummaryCards data={undefined} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
    expect(screen.getByText('Avg R')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('SummaryCards — success state', () => {
  it('renders all 7 KPI card titles', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Expectancy')).toBeInTheDocument();
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument();
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
    expect(screen.getByText('Avg R')).toBeInTheDocument();
  });

  it('formats Net P&L as currency', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('$1,250.50')).toBeInTheDocument();
  });

  it('formats Win Rate as percentage', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('65.00%')).toBeInTheDocument();
  });

  it('formats Profit Factor as ratio with 4 decimals', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('1.8500')).toBeInTheDocument();
  });

  it('formats Total Trades with locale number', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('342')).toBeInTheDocument();
  });

  it('formats Avg R as decimal with 2 places', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('1.35')).toBeInTheDocument();
  });

  it('shows green text for positive Net P&L', () => {
    render(
      <SummaryCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const pnl = screen.getByText('$1,250.50');
    expect(pnl.className).toContain('text-green-600');
  });

  it('shows red text for negative Net P&L', () => {
    const neg = { ...mockData, performance: { ...mockData.performance, net_pnl: -500 } };
    render(<SummaryCards data={neg} isLoading={false} isError={false} error={null} />);
    const v = screen.getByText('-$500.00');
    expect(v.className).toContain('text-red-600');
  });

  it('shows neutral when Net P&L is zero', () => {
    const z = { ...mockData, performance: { ...mockData.performance, net_pnl: 0 } };
    render(<SummaryCards data={z} isLoading={false} isError={false} error={null} />);
    const v = screen.getByText('$0.00');
    expect(v.className).toContain('text-gray-900');
  });

  it('shows 0 for Total Trades when data is missing', () => {
    const noTrades = { ...mockData, total_trades_all: undefined };
    render(<SummaryCards data={noTrades} isLoading={false} isError={false} error={null} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('shows 0.00 for Avg R when data is missing', () => {
    const noAvg = { ...mockData, performance: { ...mockData.performance, avg_r_multiple: undefined } };
    render(<SummaryCards data={noAvg} isLoading={false} isError={false} error={null} />);
    expect(screen.getByText('0.00')).toBeInTheDocument();
  });
});
