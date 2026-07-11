import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { Card } from '../../../shared/ui/Card';
import { EdgeStabilityIndicator } from './EdgeStabilityIndicator';
import { formatCurrency, formatDecimal, formatRatio } from '../../analytics/utils/formatters';

const BORDER_COLORS = {
  high: 'border-l-green-500',
  medium: 'border-l-yellow-400',
  low: 'border-l-gray-400',
  insufficient: 'border-l-red-400',
};

/**
 * Visual card displaying summary metrics for a single edge.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function EdgeScoreCard({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load edge detail'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <Card>
        <div className="space-y-3">
          <Skeleton variant="text" width="180px" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="space-y-1">
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" />
            </div>
            <div className="space-y-1">
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" />
            </div>
            <div className="space-y-1">
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" />
            </div>
            <div className="space-y-1">
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" />
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (!data || !data.edge) {
    return (
      <div className="flex h-[160px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No edge data available</p>
      </div>
    );
  }

  const { edge } = data;
  const borderClass = BORDER_COLORS[edge.confidence_level] || BORDER_COLORS.insufficient;

  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm border-l-4 ${borderClass}`}>
      {/* Dimensions */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {Object.entries(edge.dimensions)
          .filter(([, v]) => v != null)
          .map(([key, value]) => (
            <span key={key} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              {key}: <strong>{value}</strong>
            </span>
          ))}
        <EdgeStabilityIndicator
          stability={edge.stability_score}
          confidenceLevel={edge.confidence_level}
        />
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricItem label="Expectancy" value={formatCurrency(edge.expectancy)} />
        <MetricItem
          label="P-Value"
          value={formatDecimal(edge.p_value)}
        />
        <MetricItem
          label="Confidence Interval"
          value={`[${formatCurrency(edge.confidence_interval[0])}, ${formatCurrency(edge.confidence_interval[1])}]`}
        />
        <MetricItem
          label="Stability"
          value={`${(edge.stability_score * 100).toFixed(0)}%`}
        />
      </div>
    </div>
  );
}

/**
 * Single metric label + value row inside the card.
 */
function MetricItem({ label, value }) {
  return (
    <div>
      <p className="mb-0.5 text-xs font-medium text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-900">{value}</p>
    </div>
  );
}
