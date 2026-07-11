import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InsightCard } from '../InsightCard';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockInsight = {
  id: 1,
  severity: 'warning',
  title: 'Drawdown threshold breached',
  message: 'Your max drawdown exceeded 15% in the last 30 days.',
  confidence_level: 'high',
  recommendation: 'Consider reducing position sizes and adding tighter stop-losses.',
  supporting_metrics: [
    { name: 'Max Drawdown', value: '18.5%', source: 'risk' },
    { name: 'Win Rate', value: '42%', source: 'analytics' },
  ],
  trade_ids: [101, 102, 103],
};

// ── Loading state ─────────────────────────────────────────────────────────

describe('InsightCard — loading state', () => {
  it('renders skeleton placeholders when isLoading is true', () => {
    const { container } = render(
      <InsightCard data={undefined} isLoading={true} isError={false} error={null} />,
    );
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });
});

// ── Error state ───────────────────────────────────────────────────────────

describe('InsightCard — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <InsightCard
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Failed to load')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('InsightCard — empty state', () => {
  it('renders "No insight data available" when data is null', () => {
    render(
      <InsightCard data={null} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No insight data available')).toBeInTheDocument();
  });

  it('renders "No insight data available" when data is undefined', () => {
    render(
      <InsightCard data={undefined} isLoading={false} isError={false} error={null} />,
    );
    expect(screen.getByText('No insight data available')).toBeInTheDocument();
  });
});

// ── Success state — severity variants ─────────────────────────────────────

describe('InsightCard — success state', () => {
  it('renders severity badge', () => {
    render(
      <InsightCard
        data={mockInsight}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Warning')).toBeInTheDocument();
  });

  it('renders title and message', () => {
    render(
      <InsightCard
        data={mockInsight}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Drawdown threshold breached')).toBeInTheDocument();
    expect(
      screen.getByText('Your max drawdown exceeded 15% in the last 30 days.'),
    ).toBeInTheDocument();
  });

  it('renders confidence level indicator', () => {
    render(
      <InsightCard
        data={mockInsight}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText(/Confidence:/)).toBeInTheDocument();
    expect(screen.getByText(/High/)).toBeInTheDocument();
  });

  it('renders recommendation when present', () => {
    render(
      <InsightCard
        data={mockInsight}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText(/Recommendation:/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Consider reducing position sizes and adding tighter stop-losses./,
      ),
    ).toBeInTheDocument();
  });

  it('does not render recommendation section when recommendation is missing', () => {
    const insightWithoutRec = { ...mockInsight, recommendation: undefined };
    render(
      <InsightCard
        data={insightWithoutRec}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.queryByText(/Recommendation:/)).not.toBeInTheDocument();
  });

  it('fires onClick when clicked and onClick is provided', () => {
    const onClick = vi.fn();
    render(
      <InsightCard
        data={mockInsight}
        isLoading={false}
        isError={false}
        error={null}
        onClick={onClick}
      />,
    );
    fireEvent.click(screen.getByText('Drawdown threshold breached').closest('[role="button"]'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

// ── Severity colour variants ──────────────────────────────────────────────

describe('InsightCard — severity variants', () => {
  it('applies red border for critical severity', () => {
    const critical = { ...mockInsight, severity: 'critical' };
    const { container } = render(
      <InsightCard
        data={critical}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-red-500');
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('applies yellow border for warning severity', () => {
    const warning = { ...mockInsight, severity: 'warning' };
    const { container } = render(
      <InsightCard
        data={warning}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-yellow-400');
    expect(screen.getByText('Warning')).toBeInTheDocument();
  });

  it('applies blue border for info severity', () => {
    const info = { ...mockInsight, severity: 'info' };
    const { container } = render(
      <InsightCard
        data={info}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-blue-500');
    expect(screen.getByText('Info')).toBeInTheDocument();
  });

  it('defaults to info when severity is missing', () => {
    const noSeverity = { ...mockInsight, severity: undefined };
    const { container } = render(
      <InsightCard
        data={noSeverity}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const card = container.querySelector('.border-l-4');
    expect(card.className).toContain('border-l-blue-500');
    expect(screen.getByText('Info')).toBeInTheDocument();
  });
});
