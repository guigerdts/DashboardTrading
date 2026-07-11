import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CorrelationMatrix } from '../components/CorrelationMatrix';

// ── Mock data ───────────────────────────────────────────────────────────────

const mockData = {
  pairs: [
    { asset_a: 'AAPL', asset_b: 'MSFT', pearson_r: 0.65, trade_count: 45 },
    { asset_a: 'AAPL', asset_b: 'GOOG', pearson_r: -0.32, trade_count: 38 },
    { asset_a: 'MSFT', asset_b: 'GOOG', pearson_r: null, trade_count: 12 },
  ],
};

// ── Loading state ───────────────────────────────────────────────────────────

describe('CorrelationMatrix — loading state', () => {
  it('renders skeleton when isLoading is true', () => {
    const { container } = render(
      <CorrelationMatrix data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ─────────────────────────────────────────────────────────────

describe('CorrelationMatrix — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <CorrelationMatrix
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Correlation error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Correlation error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <CorrelationMatrix
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load correlation data')).toBeInTheDocument();
  });
});

// ── Empty state ─────────────────────────────────────────────────────────────

describe('CorrelationMatrix — empty state', () => {
  it('shows "Add more assets" message when pairs is empty array', () => {
    render(
      <CorrelationMatrix
        data={{ pairs: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Add more assets to calculate correlations')).toBeInTheDocument();
  });

  it('shows "Add more assets" message when data is null', () => {
    render(
      <CorrelationMatrix data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Add more assets to calculate correlations')).toBeInTheDocument();
  });
});

// ── Success state ───────────────────────────────────────────────────────────

describe('CorrelationMatrix — success state', () => {
  it('renders section title', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Asset Correlation')).toBeInTheDocument();
  });

  it('renders asset pair names', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getAllByText('AAPL').length).toBe(2);
    expect(screen.getAllByText('MSFT').length).toBe(2);
    expect(screen.getAllByText('GOOG').length).toBe(2);
  });

  it('shows green text for positive correlation', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const rValue = screen.getByText('0.6500');
    expect(rValue.className).toContain('text-green-600');
  });

  it('shows red text for negative correlation', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const rValue = screen.getByText('-0.3200');
    expect(rValue.className).toContain('text-red-600');
  });

  it('shows em-dash for pairs below min_trades threshold', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    const dash = screen.getAllByText('\u2014');
    expect(dash.length).toBeGreaterThanOrEqual(1);
  });

  it('renders trade counts', () => {
    render(
      <CorrelationMatrix data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('45')).toBeInTheDocument();
    expect(screen.getByText('38')).toBeInTheDocument();
  });
});
