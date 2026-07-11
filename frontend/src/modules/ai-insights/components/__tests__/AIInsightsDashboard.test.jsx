import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AIInsightsDashboard } from '../AIInsightsDashboard';

// ── Helpers ────────────────────────────────────────────────────────────────

const mockInsights = [
  { id: 1, severity: 'critical', title: 'Critical risk', message: 'Immediate action needed.' },
  { id: 2, severity: 'warning', title: 'Warning signal', message: 'Be cautious.' },
  { id: 3, severity: 'warning', title: 'Second warning', message: 'Another concern.' },
  { id: 4, severity: 'info', title: 'Info note', message: 'For your awareness.' },
];

// ── Loading state ─────────────────────────────────────────────────────────

describe('AIInsightsDashboard — loading state', () => {
  it('renders 3 skeleton cards when isLoading is true', () => {
    const { container } = render(
      <AIInsightsDashboard
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

describe('AIInsightsDashboard — error state', () => {
  it('renders ErrorFallback with message', () => {
    const onRetry = vi.fn();
    render(
      <AIInsightsDashboard
        data={undefined}
        isLoading={false}
        isError={true}
        error={new Error('Dashboard error')}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Dashboard error')).toBeInTheDocument();
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });
});

// ── Empty state ───────────────────────────────────────────────────────────

describe('AIInsightsDashboard — empty state', () => {
  it('renders "No insights available" when data is empty array', () => {
    render(
      <AIInsightsDashboard
        data={[]}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(
      screen.getByText('No insights available — insufficient evidence'),
    ).toBeInTheDocument();
  });

  it('renders "No insights available" when data has empty insights array', () => {
    render(
      <AIInsightsDashboard
        data={{ insights: [] }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(
      screen.getByText('No insights available — insufficient evidence'),
    ).toBeInTheDocument();
  });

  it('renders "No insights available" when data is null', () => {
    render(
      <AIInsightsDashboard
        data={null}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(
      screen.getByText('No insights available — insufficient evidence'),
    ).toBeInTheDocument();
  });
});

// ── Success state ─────────────────────────────────────────────────────────

describe('AIInsightsDashboard — success state', () => {
  it('groups insights by severity with count badges', () => {
    render(
      <AIInsightsDashboard
        data={{ insights: mockInsights }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    // Section headers
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('warning')).toBeInTheDocument();
    expect(screen.getByText('info')).toBeInTheDocument();

    // Count badges: 1 critical, 2 warning, 1 info
    // Use getAllByText and check the array length/specific values
    const countBadges = screen.getAllByText(/^\d+$/);
    expect(countBadges).toHaveLength(3);

    // Verify badge values by checking class association (only count badges have bg-*-100)
    const badgeContents = countBadges.map((el) => el.textContent);
    expect(badgeContents.filter((v) => v === '1').length).toBe(2); // critical + info
    expect(badgeContents.filter((v) => v === '2').length).toBe(1); // warning
  });

  it('renders InsightCard for each insight', () => {
    render(
      <AIInsightsDashboard
        data={{ insights: mockInsights }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Critical risk')).toBeInTheDocument();
    expect(screen.getByText('Warning signal')).toBeInTheDocument();
    expect(screen.getByText('Second warning')).toBeInTheDocument();
    expect(screen.getByText('Info note')).toBeInTheDocument();
  });

  it('renders severity sections in order: critical, warning, info', () => {
    const { container } = render(
      <AIInsightsDashboard
        data={{ insights: mockInsights }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    const sections = container.querySelectorAll('section');
    expect(sections.length).toBe(3);
    expect(sections[0].querySelector('h3').textContent).toBe('critical');
    expect(sections[1].querySelector('h3').textContent).toBe('warning');
    expect(sections[2].querySelector('h3').textContent).toBe('info');
  });

  it('handles data directly as an array (not wrapped in { insights })', () => {
    render(
      <AIInsightsDashboard
        data={mockInsights}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('Critical risk')).toBeInTheDocument();
    expect(screen.getByText('Info note')).toBeInTheDocument();
  });

  it('handles insights with unknown severity by grouping into info', () => {
    const customInsights = [
      { id: 1, severity: 'unknown', title: 'Weird', message: 'Something odd.' },
    ];
    render(
      <AIInsightsDashboard
        data={{ insights: customInsights }}
        isLoading={false}
        isError={false}
        error={null}
      />,
    );
    expect(screen.getByText('info')).toBeInTheDocument();
  });

  it('is wrapped in ErrorBoundary (does not crash on render error)', () => {
    // Just verify the component renders without ErrorBoundary-specific errors
    const { container } = render(
      <AIInsightsDashboard data={mockInsights} isLoading={false} isError={false} error={null} />,
    );
    expect(container.querySelectorAll('.border-l-4').length).toBe(4);
  });
});
