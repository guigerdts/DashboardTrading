import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InsightDetail } from '../InsightDetail';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockDetail = {
  id: 1,
  severity: 'critical',
  title: 'Risk limit approaching',
  message: 'Your portfolio drawdown is nearing the configured limit.',
  confidence_level: 'high',
  recommendation: 'Review open positions and consider hedging.',
  supporting_metrics: [
    { name: 'Current Drawdown', value: '14.2%', source: 'risk' },
    { name: 'Max Drawdown Limit', value: '15%', source: 'config' },
    { name: 'Daily P&L', value: '-$2,450', source: 'analytics' },
  ],
  trade_ids: [201, 202, 203, 204],
  context_snapshot: {
    evaluated_at: '2025-06-15T14:30:00Z',
    trade_count: 145,
    date_range: '2025-05-15 to 2025-06-15',
  },
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('InsightDetail — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <InsightDetail data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('InsightDetail — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <InsightDetail
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
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('InsightDetail — empty state', () => {
  it('renders "No insight detail available" when data is null', () => {
    render(
      <InsightDetail data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No insight detail available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('InsightDetail — success state', () => {
  it('renders the insight summary card with title', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Title appears in both InsightCard and EvidenceChain (fallback for rule_name)
    const titleElements = screen.getAllByText('Risk limit approaching');
    expect(titleElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders supporting metrics table', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Supporting Metrics')).toBeInTheDocument();
    expect(screen.getByText('Current Drawdown')).toBeInTheDocument();
    expect(screen.getByText('14.2%')).toBeInTheDocument();
    expect(screen.getByText('Daily P&L')).toBeInTheDocument();
    expect(screen.getByText('-$2,450')).toBeInTheDocument();
  });

  it('renders source badges in metrics table', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('analytics')).toBeInTheDocument();
    expect(screen.getByText('risk')).toBeInTheDocument();
  });

  it('renders trade IDs section', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // "Related Trades" appears in both InsightDetail and EvidenceChain
    const relatedTradeElements = screen.getAllByText('Related Trades');
    expect(relatedTradeElements.length).toBeGreaterThanOrEqual(1);
    // Trade IDs appear in both the detail section and the evidence chain
    const trade201Elements = screen.getAllByText('#201');
    expect(trade201Elements.length).toBeGreaterThanOrEqual(1);
    const trade204Elements = screen.getAllByText('#204');
    expect(trade204Elements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders context snapshot metadata', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Context Snapshot')).toBeInTheDocument();
    expect(screen.getByText('Evaluated At')).toBeInTheDocument();
    expect(screen.getByText('2025-06-15T14:30:00Z')).toBeInTheDocument();
    expect(screen.getByText('Trade Count')).toBeInTheDocument();
    expect(screen.getByText('145')).toBeInTheDocument();
  });

  it('renders evidence chain section', () => {
    render(
      <InsightDetail
        data={mockDetail}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Evidence Chain')).toBeInTheDocument();
  });

  it('handles data without supporting_metrics gracefully', () => {
    const noMetrics = { ...mockDetail, supporting_metrics: [] };
    render(
      <InsightDetail
        data={noMetrics}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText('Supporting Metrics')).not.toBeInTheDocument();
  });

  it('handles data without trade_ids gracefully', () => {
    const noTrades = { ...mockDetail, trade_ids: [] };
    render(
      <InsightDetail
        data={noTrades}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText('Related Trades')).not.toBeInTheDocument();
  });

  it('handles data without context_snapshot gracefully', () => {
    const noContext = { ...mockDetail, context_snapshot: undefined };
    render(
      <InsightDetail
        data={noContext}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText('Context Snapshot')).not.toBeInTheDocument();
  });
});
