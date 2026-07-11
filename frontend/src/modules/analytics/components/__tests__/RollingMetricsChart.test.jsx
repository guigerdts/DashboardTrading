import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RollingMetricsChart } from '../RollingMetricsChart';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockPoints = [
  { index: 1, win_rate: 0.6, profit_factor: 1.5, expectancy: 0.25, avg_r_multiple: 1.2, trade_count: 30 },
  { index: 2, win_rate: 0.65, profit_factor: 1.8, expectancy: 0.35, avg_r_multiple: 1.4, trade_count: 30 },
  { index: 3, win_rate: 0.55, profit_factor: 1.3, expectancy: 0.15, avg_r_multiple: 0.9, trade_count: 30 },
];

const mockData = {
  window_size: 30,
  points: mockPoints,
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('RollingMetricsChart — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <RollingMetricsChart data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('RollingMetricsChart — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <RollingMetricsChart
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Rolling error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Rolling error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <RollingMetricsChart
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load rolling metrics')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('RollingMetricsChart — empty state', () => {
  it('shows "Insufficient data" when points is empty array', () => {
    render(
      <RollingMetricsChart
        data={{ window_size: 30, points: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Insufficient data')).toBeInTheDocument();
  });

  it('shows "Insufficient data" when points is undefined', () => {
    render(
      <RollingMetricsChart
        data={{ window_size: 30, points: undefined }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Insufficient data')).toBeInTheDocument();
  });

  it('shows "Insufficient data" when data is null', () => {
    render(
      <RollingMetricsChart data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Insufficient data')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('RollingMetricsChart — success state', () => {
  it('renders the chart title', () => {
    render(
      <RollingMetricsChart data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Rolling Metrics')).toBeInTheDocument();
  });

  it('shows window size information', () => {
    render(
      <RollingMetricsChart data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText(/Window size: 30 trades/)).toBeInTheDocument();
  });

  it('shows data points count', () => {
    render(
      <RollingMetricsChart data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText(/3 data points/)).toBeInTheDocument();
  });

  it('renders chart container with ResponsiveContainer', () => {
    const { container } = render(
      <RollingMetricsChart data={mockData} isLoading={false} isError={false} error={null} />,
    );
    // Recharts renders ResponsiveContainer wrapper in jsdom
    const wrapper = container.querySelector('.recharts-responsive-container, .recharts-wrapper');
    expect(wrapper).toBeInTheDocument();
  });
});
