import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RHistogram } from '../RHistogram';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockBuckets = [
  { bucket: '-3R', count: 2 },
  { bucket: '-2R', count: 5 },
  { bucket: '-1R', count: 12 },
  { bucket: '0R', count: 8 },
  { bucket: '+1R', count: 15 },
  { bucket: '+2R', count: 7 },
  { bucket: '+3R', count: 3 },
];

const mockData = {
  total_trades: 52,
  buckets: mockBuckets,
  trades_without_risk: 3,
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('RHistogram — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <RHistogram data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('RHistogram — error state', () => {
  it('renders ErrorFallback with error.message', () => {
    const onRetry = vi.fn();
    render(
      <RHistogram
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('R distribution error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('R distribution error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('renders fallback message when error has no message', () => {
    render(
      <RHistogram
        data={undefined}
        isLoading={false}
        isError={true}
        error={{}}
      />,
    );
    expect(screen.getByText('Failed to load R distribution')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('RHistogram — empty state', () => {
  it('shows empty message when buckets is empty array', () => {
    render(
      <RHistogram data={{ buckets: [], total_trades: 0 }} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No R multiple data available')).toBeInTheDocument();
  });

  it('shows empty message when buckets is undefined', () => {
    render(
      <RHistogram data={{ buckets: undefined }} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No R multiple data available')).toBeInTheDocument();
  });

  it('shows empty message when data is null', () => {
    render(
      <RHistogram data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No R multiple data available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('RHistogram — success state', () => {
  it('renders the chart title', () => {
    render(
      <RHistogram data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('R Multiple Distribution')).toBeInTheDocument();
  });

  it('shows trades without risk count', () => {
    render(
      <RHistogram data={mockData} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('Trades without risk: 3')).toBeInTheDocument();
  });

  it('does not show trades without risk when count is 0', () => {
    render(
      <RHistogram
        data={{ buckets: mockBuckets, total_trades: 52, trades_without_risk: 0 }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText(/Trades without risk/)).not.toBeInTheDocument();
  });

  it('handles empty dataset gracefully', () => {
    render(
      <RHistogram data={{ buckets: [], total_trades: 0 }} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No R multiple data available')).toBeInTheDocument();
  });
});
