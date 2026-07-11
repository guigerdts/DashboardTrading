import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HeatmapChart } from '../HeatmapChart';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockCells = [
  { day: 0, hour: 9, trade_count: 5, net_pnl: 250 },
  { day: 0, hour: 10, trade_count: 3, net_pnl: -100 },
  { day: 1, hour: 14, trade_count: 8, net_pnl: 500 },
  { day: 2, hour: 9, trade_count: 2, net_pnl: 50 },
  { day: 3, hour: 15, trade_count: 6, net_pnl: 300 },
  { day: 4, hour: 10, trade_count: 4, net_pnl: -50 },
];

// ── Loading state ─────────────────────────────────────────────────────────

describe('HeatmapChart — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <HeatmapChart data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('HeatmapChart — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <HeatmapChart
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Heatmap error')}
        onRetry={onRetry}
      />,
    );
    // ErrorFallback shows error.message
    expect(screen.getByText('Heatmap error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <HeatmapChart
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load heatmap')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('HeatmapChart — empty state', () => {
  it('shows "No heatmap data available" when cells is empty array', () => {
    render(
      <HeatmapChart
        data={{ cells: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No heatmap data available')).toBeInTheDocument();
  });

  it('shows "No heatmap data available" when cells is undefined', () => {
    render(
      <HeatmapChart
        data={{ cells: undefined }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No heatmap data available')).toBeInTheDocument();
  });

  it('shows "No heatmap data available" when data is null', () => {
    render(
      <HeatmapChart data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No heatmap data available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('HeatmapChart — success state', () => {
  const mockCells = [
    { day: 0, hour: 9, trade_count: 5, net_pnl: 250 },
    { day: 0, hour: 10, trade_count: 3, net_pnl: -100 },
    { day: 1, hour: 14, trade_count: 8, net_pnl: 500 },
    { day: 2, hour: 9, trade_count: 2, net_pnl: 50 },
    { day: 3, hour: 15, trade_count: 6, net_pnl: 300 },
    { day: 4, hour: 10, trade_count: 4, net_pnl: -50 },
  ];

  it('renders the chart title', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Trading Heatmap')).toBeInTheDocument();
  });

  it('renders day labels (Mon-Sun)', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Tue')).toBeInTheDocument();
    expect(screen.getByText('Wed')).toBeInTheDocument();
    expect(screen.getByText('Thu')).toBeInTheDocument();
    expect(screen.getByText('Fri')).toBeInTheDocument();
    expect(screen.getByText('Sat')).toBeInTheDocument();
    expect(screen.getByText('Sun')).toBeInTheDocument();
  });

  it('renders hour labels (00-23)', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('00')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('23')).toBeInTheDocument();
  });

  it('renders trade counts in cells', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('6')).toBeInTheDocument();
  });

  it('sets title attribute for cells with data', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Mon 09:00 cell should have title with trade count and P&L
    const cell = screen.getByTitle('Mon 09:00 — 5 trades, $250.00');
    expect(cell).toBeInTheDocument();
  });

  it('does not set title for empty cells', () => {
    render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Empty cells should not have a title attribute
    const allCells = document.querySelectorAll('[class*="bg-gray-50"]');
    allCells.forEach((cell) => {
      expect(cell.getAttribute('title')).toBeFalsy();
    });
  });

  it('renders 7×24 grid (168 cells + 7 day labels + 24 hour labels + 1 corner)', () => {
    const { container } = render(
      <HeatmapChart
        data={{ cells: mockCells }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const grid = container.querySelector('.grid');
    expect(grid).toBeInTheDocument();
    // 7 day labels + 24 hour labels + 1 corner + 168 cells = 200
    expect(grid.children.length).toBe(200);
  });
});
