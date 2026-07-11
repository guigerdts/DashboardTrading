import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskMetricsCards } from '../components/RiskMetricsCards';

// ── Mock data ───────────────────────────────────────────────────────────────

const mockData = {
  total_trades: 100,
  max_consecutive_wins: 8,
  max_consecutive_losses: 4,
  avg_holding_time_hours: 6.5,
  avg_risk_per_trade: 125.0,
  trades_without_risk: 5,
  avg_risk_utilization: 0.035,
  trades_without_position: 10,
  kelly_fraction: 0.125,
  risk_of_ruin: 0.0015,
  expectancy_adjusted: 0.85,
  capital: 50000,
};

// ── Loading state ───────────────────────────────────────────────────────────

describe('RiskMetricsCards — loading state', () => {
  it('renders skeleton containers when isLoading is true', () => {
    const { container } = render(
      <RiskMetricsCards data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBe(16);
  });
});

// ── Error state ─────────────────────────────────────────────────────────────

describe('RiskMetricsCards — error state', () => {
  it('renders ErrorFallback with message and retry button', () => {
    const onRetry = vi.fn();
    render(
      <RiskMetricsCards
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Risk API error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Risk API error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <RiskMetricsCards
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load risk metrics')).toBeInTheDocument();
  });
});

// ── Empty state ─────────────────────────────────────────────────────────────

describe('RiskMetricsCards — empty state', () => {
  it('renders all 8 card titles when data is null', () => {
    render(
      <RiskMetricsCards data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Max Consecutive Wins')).toBeInTheDocument();
    expect(screen.getByText('Max Consecutive Losses')).toBeInTheDocument();
    expect(screen.getByText('Avg Holding Time')).toBeInTheDocument();
    expect(screen.getByText('Avg Risk / Trade')).toBeInTheDocument();
    expect(screen.getByText('Risk Utilization')).toBeInTheDocument();
    expect(screen.getByText('Kelly Fraction')).toBeInTheDocument();
    expect(screen.getByText('Risk of Ruin')).toBeInTheDocument();
    expect(screen.getByText('Expectancy Adj.')).toBeInTheDocument();
  });

  it('renders all 8 card titles when data is undefined', () => {
    render(
      <RiskMetricsCards data={undefined} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Max Consecutive Wins')).toBeInTheDocument();
    expect(screen.getByText('Max Consecutive Losses')).toBeInTheDocument();
    expect(screen.getByText('Expectancy Adj.')).toBeInTheDocument();
  });
});

// ── Success state ───────────────────────────────────────────────────────────

describe('RiskMetricsCards — success state', () => {
  it('renders all 8 card titles', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Max Consecutive Wins')).toBeInTheDocument();
    expect(screen.getByText('Max Consecutive Losses')).toBeInTheDocument();
    expect(screen.getByText('Avg Holding Time')).toBeInTheDocument();
    expect(screen.getByText('Avg Risk / Trade')).toBeInTheDocument();
    expect(screen.getByText('Risk Utilization')).toBeInTheDocument();
    expect(screen.getByText('Kelly Fraction')).toBeInTheDocument();
    expect(screen.getByText('Risk of Ruin')).toBeInTheDocument();
    expect(screen.getByText('Expectancy Adj.')).toBeInTheDocument();
  });

  it('displays max consecutive wins in green', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const el = screen.getByText('8');
    expect(el.className).toContain('text-green-600');
  });

  it('displays max consecutive losses in red', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const el = screen.getByText('4');
    expect(el.className).toContain('text-red-600');
  });

  it('formats Avg Holding Time with hours suffix', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('6.5h')).toBeInTheDocument();
  });

  it('formats Avg Risk / Trade as currency', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('$125.00')).toBeInTheDocument();
  });

  it('formats Risk Utilization as percentage', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('3.50%')).toBeInTheDocument();
  });

  it('formats Kelly Fraction as ratio', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('0.1250')).toBeInTheDocument();
  });

  it('formats Risk of Ruin as percentage', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('0.15%')).toBeInTheDocument();
  });

  it('formats Expectancy Adjusted as ratio', () => {
    render(
      <RiskMetricsCards data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('0.8500')).toBeInTheDocument();
  });

  it('shows em-dash for null metrics', () => {
    const partialData = { ...mockData, avg_risk_per_trade: null, kelly_fraction: null };
    render(
      <RiskMetricsCards data={partialData} isLoading={false} isError={false} error={null} />,
    );
    const dashes = screen.getAllByText('\u2014');
    expect(dashes.length).toBe(2);
  });
});
