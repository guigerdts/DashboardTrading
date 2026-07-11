import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExposureTable } from '../components/ExposureTable';

// ── Mock data ───────────────────────────────────────────────────────────────

const byAssetData = {
  records: [
    { asset_id: 1, symbol: 'AAPL', notional: 50000, trade_count: 25, total_pnl: 1200 },
    { asset_id: 2, symbol: 'MSFT', notional: 30000, trade_count: 18, total_pnl: -400 },
  ],
};

const bySessionData = {
  records: [
    { session_name: 'London', trade_count: 30 },
    { session_name: 'New York', trade_count: 22 },
  ],
};

const byStrategyData = {
  records: [
    { strategy_name: 'Trend Following', trade_count: 15, total_risk_amount: 4500 },
    { strategy_name: 'Mean Reversion', trade_count: 10, total_risk_amount: 3200 },
  ],
};

// ── Loading state ───────────────────────────────────────────────────────────

describe('ExposureTable — loading state', () => {
  it('renders skeleton when isLoading is true', () => {
    const { container } = render(
      <ExposureTable
        byAssetData={undefined}
        bySessionData={undefined}
        byStrategyData={undefined}
        isLoading={true}
        isError={false}
        error={null}
      />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ─────────────────────────────────────────────────────────────

describe('ExposureTable — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <ExposureTable
        byAssetData={undefined}
        bySessionData={undefined}
        byStrategyData={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Exposure error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Exposure error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ─────────────────────────────────────────────────────────────

describe('ExposureTable — empty state', () => {
  it('shows "No asset exposure data" when asset records is empty array', () => {
    render(
      <ExposureTable
        byAssetData={{ records: [] }}
        bySessionData={{ records: [] }}
        byStrategyData={{ records: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('No asset exposure data')).toBeInTheDocument();
  });
});

// ── Success state ───────────────────────────────────────────────────────────

describe('ExposureTable — success state', () => {
  it('renders section title', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Exposure')).toBeInTheDocument();
  });

  it('renders tab buttons', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('By Asset')).toBeInTheDocument();
    expect(screen.getByText('By Session')).toBeInTheDocument();
    expect(screen.getByText('By Strategy')).toBeInTheDocument();
  });

  it('shows asset data in By Asset tab by default', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('MSFT')).toBeInTheDocument();
    expect(screen.getByText('$50,000.00')).toBeInTheDocument();
    expect(screen.getByText('$30,000.00')).toBeInTheDocument();
  });

  it('switches to By Session tab on click', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    fireEvent.click(screen.getByText('By Session'));
    expect(screen.getByText('London')).toBeInTheDocument();
    expect(screen.getByText('New York')).toBeInTheDocument();
  });

  it('switches to By Strategy tab on click', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    fireEvent.click(screen.getByText('By Strategy'));
    expect(screen.getByText('Trend Following')).toBeInTheDocument();
    expect(screen.getByText('Mean Reversion')).toBeInTheDocument();
    expect(screen.getByText('$4,500.00')).toBeInTheDocument();
    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
  });

  it('shows green text for positive P&L and red for negative', () => {
    render(
      <ExposureTable
        byAssetData={byAssetData}
        bySessionData={bySessionData}
        byStrategyData={byStrategyData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const pnlPositive = screen.getByText('$1,200.00');
    expect(pnlPositive.className).toContain('text-green-600');
    const pnlNegative = screen.getByText('-$400.00');
    expect(pnlNegative.className).toContain('text-red-600');
  });
});
