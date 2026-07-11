import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatNumber } from '../../analytics/utils/formatters';

/**
 * Correlation matrix table showing asset pair correlations.
 * Positive correlations highlighted green, negative red.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function CorrelationMatrix({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load correlation data'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="140px" className="mb-4" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="mb-3 flex gap-4">
            <Skeleton variant="rect" height={24} width="18%" />
            <Skeleton variant="rect" height={24} width="18%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="14%" />
          </div>
        ))}
      </div>
    );
  }

  const pairs = data?.pairs;
  if (!pairs || pairs.length === 0) {
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Asset Correlation</h2>
        <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
          <p className="text-gray-400">Add more assets to calculate correlations</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Asset Correlation</h2>
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Asset A</th>
                <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Asset B</th>
                <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Correlation</th>
                <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Trades</th>
              </tr>
            </thead>
            <tbody>
              {pairs.map((pair, idx) => {
                const r = pair.pearson_r;
                const displayR = r != null ? r.toFixed(4) : '\u2014';
                const colorClass =
                  r != null
                    ? r > 0
                      ? 'text-green-600'
                      : r < 0
                        ? 'text-red-600'
                        : 'text-gray-700'
                    : 'text-gray-400';

                return (
                  <tr
                    key={`${pair.asset_a}-${pair.asset_b}`}
                    className="border-b border-gray-100 last:border-0"
                  >
                    <td className="py-2 pr-2 font-medium text-gray-900">{pair.asset_a}</td>
                    <td className="py-2 pr-2 font-medium text-gray-900">{pair.asset_b}</td>
                    <td className={`py-2 pr-2 font-medium ${colorClass}`}>{displayR}</td>
                    <td className="py-2 text-gray-700">{formatNumber(pair.trade_count)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
