import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { EdgeStabilityIndicator } from './EdgeStabilityIndicator';
import { formatCurrency, formatDecimal } from '../../analytics/utils/formatters';

/**
 * Sortable table of all edge rankings.
 * Rows link to the edge detail page on click.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void, showInsufficient: boolean, onToggleInsufficient?: () => void }} props
 */
export function EdgeRankingTable({
  data,
  isLoading,
  isError,
  error,
  onRetry,
  showInsufficient,
  onToggleInsufficient,
}) {
  const navigate = useNavigate();

  const rankings = data?.rankings;

  const sortedRankings = useMemo(() => {
    if (!rankings || rankings.length === 0) return [];
    return [...rankings].sort((a, b) => (b.edge_score ?? 0) - (a.edge_score ?? 0));
  }, [rankings]);

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load edge rankings'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="160px" className="mb-4" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="mb-3 flex gap-4">
            <Skeleton variant="rect" height={24} width="18%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="16%" />
            <Skeleton variant="rect" height={24} width="12%" />
            <Skeleton variant="rect" height={24} width="14%" />
          </div>
        ))}
      </div>
    );
  }

  if (!rankings || rankings.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No edges found</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">
          Edge Rankings ({sortedRankings.length})
        </h3>
        {onToggleInsufficient && (
          <label className="flex items-center gap-2 text-xs text-gray-500">
            <input
              type="checkbox"
              checked={showInsufficient}
              onChange={onToggleInsufficient}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Show insufficient
          </label>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Dimensions
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Edge Score
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Expectancy
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Trades
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                CI (95%)
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Stability
              </th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Level
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedRankings.map((edge) => {
              const pnl = edge.expectancy ?? 0;
              return (
                <tr
                  key={edge.group_id}
                  onClick={() => navigate(`/analytics/edges/${edge.group_id}`)}
                  className="cursor-pointer border-b border-gray-100 last:border-0 hover:bg-gray-50"
                >
                  <td className="py-2 pr-2 font-medium text-gray-900">
                    {Object.entries(edge.dimensions)
                      .filter(([, v]) => v != null)
                      .map(([, v]) => v)
                      .join(' · ')}
                  </td>
                  <td className="py-2 pr-2 font-medium text-gray-900">
                    {formatDecimal(edge.edge_score)}
                  </td>
                  <td
                    className={`py-2 pr-2 ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : ''
                    }`}
                  >
                    {formatCurrency(pnl)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {edge.trade_count}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatCurrency(edge.confidence_interval[0])} – {formatCurrency(edge.confidence_interval[1])}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {(edge.stability_score * 100).toFixed(0)}%
                  </td>
                  <td className="py-2">
                    <EdgeStabilityIndicator
                      stability={edge.stability_score}
                      confidenceLevel={edge.confidence_level}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
