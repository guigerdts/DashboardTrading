import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { InsightCard } from './InsightCard';
import { EvidenceChain } from './EvidenceChain';

/**
 * Full detail view for a single AI insight.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function InsightDetail({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load insight detail'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton variant="text" width="240px" />
        <Skeleton variant="rect" height={120} width="100%" />
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="rect" height={80} width="100%" />
        <Skeleton variant="rect" height={80} width="100%" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-[160px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No insight detail available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Insight summary card (read-only, no interactivity) */}
      <InsightCard data={data} />

      {/* Supporting metrics table */}
      {data.supporting_metrics && data.supporting_metrics.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">
            Supporting Metrics
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Name
                  </th>
                  <th className="pb-2 pr-4 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Value
                  </th>
                  <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.supporting_metrics.map((metric, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-gray-100 last:border-0"
                  >
                    <td className="py-2 pr-4 font-medium text-gray-900">
                      {metric.name}
                    </td>
                    <td className="py-2 pr-4 text-gray-700">{metric.value}</td>
                    <td className="py-2">
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                        {metric.source}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Evidence chain */}
      <EvidenceChain data={data} />

      {/* Trade IDs */}
      {data.trade_ids && data.trade_ids.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-gray-900">
            Related Trades
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.trade_ids.map((id) => (
              <span
                key={id}
                className="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700"
              >
                #{id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Context snapshot metadata */}
      {data.context_snapshot && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-gray-900">
            Context Snapshot
          </h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {Object.entries(data.context_snapshot)
              .filter(([, v]) => v != null)
              .map(([key, value]) => (
                <div key={key}>
                  <dt className="text-xs font-medium text-gray-500">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </dt>
                  <dd className="text-gray-900">
                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </dd>
                </div>
              ))}
          </dl>
        </div>
      )}
    </div>
  );
}
