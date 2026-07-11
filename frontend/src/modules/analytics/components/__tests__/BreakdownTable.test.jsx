import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BreakdownTable } from '../BreakdownTable';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockItems = [
  {
    id: 1,
    name: 'Trend Following',
    trade_count: 50,
    win_rate: 0.68,
    net_pnl: 2500,
    gross_profit: 5000,
    gross_loss: -2500,
    profit_factor: 2.0,
    expectancy: 50.0,
    avg_win: 200,
    avg_loss: -100,
  },
  {
    id: 2,
    name: 'Mean Reversion',
    trade_count: 30,
    win_rate: 0.55,
    net_pnl: -500,
    gross_profit: 2000,
    gross_loss: -2500,
    profit_factor: 0.8,
    expectancy: -16.67,
    avg_win: 150,
    avg_loss: -120,
  },
];

// ── Loading state ─────────────────────────────────────────────────────────

describe('BreakdownTable — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <BreakdownTable
        title="Strategies"
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

describe('BreakdownTable — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <BreakdownTable
        title="Strategies"
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Failed to load')}
        onRetry={onRetry}
      />,
    );
    // ErrorFallback shows error.message, not the title-based fallback
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message with title when error has no message', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load Strategies')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('BreakdownTable — empty state', () => {
  it('shows "No data" when items array is empty', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('shows "No data" when items is undefined', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: undefined }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No data')).toBeInTheDocument();
  });

  it('shows "No data" when data is null', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={null}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No data')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('BreakdownTable — success state', () => {
  it('renders the title', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Strategies')).toBeInTheDocument();
  });

  it('renders all column headers', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Net P&L')).toBeInTheDocument();
    expect(screen.getByText('Win Rate')).toBeInTheDocument();
    expect(screen.getByText('Trades')).toBeInTheDocument();
    expect(screen.getByText('Profit Factor')).toBeInTheDocument();
    expect(screen.getByText('Avg Win')).toBeInTheDocument();
    expect(screen.getByText('Avg Loss')).toBeInTheDocument();
  });

  it('renders all item names', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Trend Following')).toBeInTheDocument();
    expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
  });

  it('sorts items by net_pnl descending', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const rows = screen.getAllByRole('row');
    // Row 0 is header, row 1 should be first item (Trend Following, net_pnl=2500)
    // Row 2 should be second item (Mean Reversion, net_pnl=-500)
    expect(rows[1]).toHaveTextContent('Trend Following');
    expect(rows[2]).toHaveTextContent('Mean Reversion');
  });

  it('formats Net P&L as currency with green for positive', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    expect(screen.getByText('$2,500.00').className).toContain('text-green-600');
  });

  it('formats Net P&L as currency with red for negative', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('-$500.00')).toBeInTheDocument();
    expect(screen.getByText('-$500.00').className).toContain('text-red-600');
  });

  it('formats Win Rate as percentage', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('68.00%')).toBeInTheDocument();
    expect(screen.getByText('55.00%')).toBeInTheDocument();
  });

  it('formats Trades with locale number', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('formats Profit Factor as ratio', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('2.0000')).toBeInTheDocument();
  });

  it('formats Avg Win and Avg Loss as currency', () => {
    render(
      <BreakdownTable
        title="Strategies"
        data={{ items: mockItems }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('$200.00')).toBeInTheDocument();
    expect(screen.getByText('$150.00')).toBeInTheDocument();
    expect(screen.getByText('-$100.00')).toBeInTheDocument();
    expect(screen.getByText('-$120.00')).toBeInTheDocument();
  });
});
