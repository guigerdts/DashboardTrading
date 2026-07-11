import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';

const SOURCE_BADGE_STYLES = {
  analytics: 'bg-green-100 text-green-700 border-green-200',
  risk: 'bg-red-100 text-red-700 border-red-200',
  edge: 'bg-purple-100 text-purple-700 border-purple-200',
  default: 'bg-gray-100 text-gray-700 border-gray-200',
};

/**
 * Renders the chain of evidence for an insight, showing data sources,
 * rules, and trade IDs in a visual timeline.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function EvidenceChain({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load evidence chain'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="140px" className="mb-3" />
        <div className="space-y-3">
          <Skeleton variant="rect" height={32} width="100%" />
          <Skeleton variant="rect" height={32} width="100%" />
          <Skeleton variant="rect" height={32} width="100%" />
        </div>
      </div>
    );
  }

  if (!data || (!data.supporting_metrics && !data.trade_ids)) {
    return (
      <div className="flex h-[100px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No evidence chain available</p>
      </div>
    );
  }

  const hasMetrics = data.supporting_metrics && data.supporting_metrics.length > 0;
  const hasTradeIds = data.trade_ids && data.trade_ids.length > 0;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-900">Evidence Chain</h3>

      <div className="relative">
        {/* Visual timeline */}
        <div className="space-y-0">
          {/* Step 1: Data Sources */}
          {hasMetrics && (
            <div className="relative flex items-start gap-4 pb-4">
              <div className="flex flex-col items-center">
                <div className="z-10 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                  1
                </div>
                <div className="mt-1 h-full w-0.5 bg-gray-200" />
              </div>
              <div className="flex-1 pt-0.5">
                <p className="mb-2 text-xs font-medium text-gray-500">Data Sources</p>
                <div className="flex flex-wrap gap-1.5">
                  {data.supporting_metrics.map((metric, idx) => (
                    <span
                      key={idx}
                      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                        SOURCE_BADGE_STYLES[metric.source] || SOURCE_BADGE_STYLES.default
                      }`}
                    >
                      {metric.source ? metric.source.charAt(0).toUpperCase() + metric.source.slice(1) : 'Unknown'}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Rule */}
          <div className="relative flex items-start gap-4 pb-4">
            <div className="flex flex-col items-center">
              <div className="z-10 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                {hasMetrics ? 2 : 1}
              </div>
              <div className="mt-1 h-full w-0.5 bg-gray-200" />
            </div>
            <div className="flex-1 pt-0.5">
              <p className="mb-1 text-xs font-medium text-gray-500">Rule</p>
              <p className="text-sm text-gray-900">
                {data.rule_name || data.title || 'Pattern detected'}
              </p>
            </div>
          </div>

          {/* Step 3: Trade IDs (if any) */}
          {hasTradeIds && (
            <div className="relative flex items-start gap-4 pb-4">
              <div className="flex flex-col items-center">
                <div className="z-10 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
                  {hasMetrics ? 3 : 2}
                </div>
                <div className="mt-1 h-full w-0.5 bg-gray-200" />
              </div>
              <div className="flex-1 pt-0.5">
                <p className="mb-1 text-xs font-medium text-gray-500">Related Trades</p>
                <div className="flex flex-wrap gap-1.5">
                  {data.trade_ids.map((id) => (
                    <span
                      key={id}
                      className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-blue-600 hover:bg-blue-50"
                    >
                      #{id}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step N: Insight */}
          <div className="relative flex items-start gap-4">
            <div className="flex flex-col items-center">
              <div className="z-10 flex h-6 w-6 items-center justify-center rounded-full bg-green-500 text-xs font-bold text-white">
                {[hasMetrics, hasTradeIds].filter(Boolean).length + 1}
              </div>
            </div>
            <div className="flex-1 pt-0.5">
              <p className="mb-1 text-xs font-medium text-gray-500">Insight Generated</p>
              <p className="text-sm font-medium text-green-700">
                {data.severity
                  ? `${data.severity.charAt(0).toUpperCase() + data.severity.slice(1)} — ${data.message || 'Insight detected'}`
                  : data.message || 'Insight detected'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
