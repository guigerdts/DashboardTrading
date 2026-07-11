import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';

const SEVERITY_STYLES = {
  critical: {
    badge: 'bg-red-100 text-red-700 border-red-200',
    dot: 'bg-red-500',
    border: 'border-l-red-500',
  },
  warning: {
    badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    dot: 'bg-yellow-400',
    border: 'border-l-yellow-400',
  },
  info: {
    badge: 'bg-blue-100 text-blue-700 border-blue-200',
    dot: 'bg-blue-500',
    border: 'border-l-blue-500',
  },
};

const CONFIDENCE_LABELS = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  insufficient: 'Insufficient',
};

const DEFAULT_SEVERITY = SEVERITY_STYLES.info;

/**
 * Visual card displaying a single AI insight.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void, onClick?: () => void }} props
 */
export function InsightCard({ data, isLoading, isError, error, onRetry, onClick }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load insight'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton variant="rect" height={22} width={70} />
            <Skeleton variant="text" width="180px" />
          </div>
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="85%" />
          <div className="flex items-center gap-3">
            <Skeleton variant="rect" height={20} width={90} />
            <Skeleton variant="rect" height={20} width={120} />
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-[120px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No insight data available</p>
      </div>
    );
  }

  const severity = data.severity || 'info';
  const style = SEVERITY_STYLES[severity] || DEFAULT_SEVERITY;

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm border-l-4 ${style.border} ${
        onClick ? 'cursor-pointer hover:bg-gray-50' : ''
      }`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') onClick();
            }
          : undefined
      }
    >
      {/* Header row: severity badge + confidence */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${style.badge}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden="true" />
          {severity.charAt(0).toUpperCase() + severity.slice(1)}
        </span>
        {data.confidence_level && (
          <span className="text-xs font-medium text-gray-500">
            Confidence:{' '}
            {CONFIDENCE_LABELS[data.confidence_level] || data.confidence_level}
          </span>
        )}
      </div>

      {/* Title & message */}
      {data.title && (
        <h4 className="mb-1 text-sm font-semibold text-gray-900">{data.title}</h4>
      )}
      {data.message && (
        <p className="mb-3 text-sm text-gray-600">{data.message}</p>
      )}

      {/* Recommendation (optional) */}
      {data.recommendation && (
        <div className="rounded-md bg-blue-50 p-2.5 text-xs text-blue-700">
          <span className="font-medium">Recommendation: </span>
          {data.recommendation}
        </div>
      )}
    </div>
  );
}
