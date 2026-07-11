import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceChain } from '../EvidenceChain';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockData = {
  id: 1,
  severity: 'warning',
  title: 'Drawdown threshold breached',
  message: 'Your max drawdown exceeded 15% in the last 30 days.',
  rule_name: 'Max Drawdown Rule',
  supporting_metrics: [
    { name: 'Max Drawdown', value: '18.5%', source: 'risk' },
    { name: 'Win Rate', value: '42%', source: 'analytics' },
    { name: 'Edge Score', value: '0.72', source: 'edge' },
  ],
  trade_ids: [101, 102, 103],
};

const mockDataNoMetrics = {
  id: 2,
  severity: 'info',
  title: 'Pattern detected',
  message: 'Reversal pattern identified.',
  trade_ids: [201],
};

const mockDataNoTrades = {
  id: 3,
  severity: 'info',
  title: 'Volume anomaly',
  message: 'Unusual volume detected.',
  supporting_metrics: [
    { name: 'Volume', value: '2.5x avg', source: 'analytics' },
  ],
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('EvidenceChain — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <EvidenceChain data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('EvidenceChain — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <EvidenceChain
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Chain error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Chain error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('EvidenceChain — empty state', () => {
  it('renders "No evidence chain available" when data is null', () => {
    render(
      <EvidenceChain data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No evidence chain available')).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('EvidenceChain — success state', () => {
  it('renders the section heading', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Evidence Chain')).toBeInTheDocument();
  });

  it('renders step numbers: Data Sources, Rule, Related Trades, Insight Generated', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Step labels
    const stepLabels = screen.getAllByText(/Data Sources|Rule|Related Trades|Insight Generated/);
    expect(stepLabels.length).toBeGreaterThanOrEqual(4);
  });

  it('renders source badges for each source type', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Risk')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Edge')).toBeInTheDocument();
  });

  it('renders rule name', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Max Drawdown Rule')).toBeInTheDocument();
  });

  it('renders trade IDs as links', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('#101')).toBeInTheDocument();
    expect(screen.getByText('#102')).toBeInTheDocument();
    expect(screen.getByText('#103')).toBeInTheDocument();
  });

  it('renders the final insight step with severity and message', () => {
    render(
      <EvidenceChain
        data={mockData}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText(/Warning/)).toBeInTheDocument();
    expect(
      screen.getByText(/Your max drawdown exceeded 15% in the last 30 days/),
    ).toBeInTheDocument();
  });

  it('handles data without supporting_metrics (fewer steps)', () => {
    render(
      <EvidenceChain
        data={mockDataNoMetrics}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Should skip "Data Sources" step, go straight to Rule
    expect(screen.queryByText('Data Sources')).not.toBeInTheDocument();
    expect(screen.getByText('Rule')).toBeInTheDocument();
    expect(screen.getByText('#201')).toBeInTheDocument();
  });

  it('handles data without trade_ids', () => {
    render(
      <EvidenceChain
        data={mockDataNoTrades}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Data Sources')).toBeInTheDocument();
    expect(screen.queryByText('Related Trades')).not.toBeInTheDocument();
    expect(screen.getByText('Insight Generated')).toBeInTheDocument();
  });

  it('handles data without rule_name by falling back to title', () => {
    const noRule = { ...mockData, rule_name: undefined };
    render(
      <EvidenceChain
        data={noRule}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Drawdown threshold breached')).toBeInTheDocument();
  });
});
