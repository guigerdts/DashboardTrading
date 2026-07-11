import { useMemo } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';
import { InsightCard } from './InsightCard';

const SEVERITY_ORDER = ['critical', 'warning', 'info'];

const SEVERITY_COUNT_STYLES = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-yellow-100 text-yellow-700',
  info: 'bg-blue-100 text-blue-700',
};

/**
 * Dashboard that groups AI insights by severity.
 * Handles loading, error, empty, and success states.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void, onInsightClick?: (insight) => void }} props
 */
function AIInsightsDashboardInner({ data, isLoading, isError, error, onRetry, onInsightClick }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load AI insights'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Skeleton variant="text" width="160px" />
          <Skeleton variant="rect" height={22} width={60} />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <InsightCard key={i} isLoading={true} />
        ))}
      </div>
    );
  }

  const insights = data?.insights || data || [];

  if (!insights || (Array.isArray(insights) && insights.length === 0)) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="text-center">
          <p className="text-gray-400">No insights available — insufficient evidence</p>
        </div>
      </div>
    );
  }

  // Normalise to array if data comes as object with insights array
  const insightList = Array.isArray(insights) ? insights : [];

  // Group by severity
  const grouped = useMemo(() => {
    const groups = { critical: [], warning: [], info: [] };
    insightList.forEach((insight) => {
      const severity = insight.severity || 'info';
      if (groups[severity]) {
        groups[severity].push(insight);
      } else {
        groups.info.push(insight);
      }
    });
    return groups;
  }, [insightList]);

  // Sort each group by confidence or a default order
  const sortedGroups = useMemo(() => {
    const sorted = {};
    SEVERITY_ORDER.forEach((sev) => {
      sorted[sev] = [...(grouped[sev] || [])];
    });
    return sorted;
  }, [grouped]);

  const hasAnyInsights = SEVERITY_ORDER.some((sev) => sortedGroups[sev].length > 0);

  if (!hasAnyInsights) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No insights available — insufficient evidence</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {SEVERITY_ORDER.map((severity) => {
        const items = sortedGroups[severity];
        if (items.length === 0) return null;

        return (
          <section key={severity}>
            <div className="mb-3 flex items-center gap-2">
              <h3 className="text-sm font-semibold capitalize text-gray-900">
                {severity}
              </h3>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                  SEVERITY_COUNT_STYLES[severity]
                }`}
              >
                {items.length}
              </span>
            </div>
            <div className="space-y-3">
              {items.map((insight, idx) => (
                <InsightCard
                  key={insight.id || idx}
                  data={insight}
                  onClick={onInsightClick ? () => onInsightClick(insight) : undefined}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

/**
 * Wrapped with ErrorBoundary for isolation.
 */
export function AIInsightsDashboard(props) {
  return (
    <ErrorBoundary>
      <AIInsightsDashboardInner {...props} />
    </ErrorBoundary>
  );
}
