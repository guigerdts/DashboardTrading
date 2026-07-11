import { Link } from 'react-router-dom';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency } from '../../analytics/utils/formatters';

/**
 * Table of trades belonging to a single edge group.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function EdgeDetailDrilldown({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load edge trades'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="120px" className="mb-4" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="mb-3 flex gap-4">
            <Skeleton variant="rect" height={24} width="10%" />
            <Skeleton variant="rect" height={24} width="16%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="12%" />
            <Skeleton variant="rect" height={24} width="12%" />
          </div>
        ))}
      </div>
    );
  }

  const trades = data?.trades;

  if (!trades || trades.length === 0) {
    return (
      <div className="flex h-[160px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No trades for this edge group</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">
        Trades ({trades.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                ID
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Strategy
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Setup
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Asset
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Direction
              </th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                P&amp;L
              </th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => {
              const pnl = trade.pnl ?? 0;
              return (
                <tr
                  key={trade.id}
                  className="border-b border-gray-100 last:border-0"
                >
                  <td className="py-2 pr-2 text-gray-900">
                    <Link
                      to={`/trades/${trade.id}`}
                      className="font-medium text-blue-600 hover:text-blue-800"
                    >
                      #{trade.id}
                    </Link>
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {trade.strategy || '\u2014'}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {trade.setup || '\u2014'}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {trade.asset || '\u2014'}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {trade.direction || '\u2014'}
                  </td>
                  <td
                    className={`py-2 font-medium ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : 'text-gray-900'
                    }`}
                  >
                    {formatCurrency(pnl)}
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
