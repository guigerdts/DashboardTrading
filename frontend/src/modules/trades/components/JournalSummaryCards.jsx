import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatPercent } from '../../analytics/utils/formatters';

/**
 * Summary stat cards for the Trading Journal.
 * Shows Total Trades, Net P&L, and Win Rate.
 *
 * @param {{
 *   data: { total_trades?: number, total_pnl?: number, win_rate?: number } | null,
 *   isLoading: boolean,
 *   isError: boolean,
 *   error: Error | null,
 *   onRetry?: () => void,
 * }} props
 */
export function JournalSummaryCards({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load summary'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="80%" className="mt-2" />
          </div>
        ))}
      </div>
    );
  }

  const totalTrades = data?.total_trades ?? 0;
  const netPnl = data?.total_pnl ?? 0;
  const winRate = data?.win_rate ?? 0;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <Card>
        <p className="mb-1 text-xs font-medium text-gray-500">Total Trades</p>
        <p className="text-2xl font-semibold text-gray-900">
          {totalTrades}
        </p>
      </Card>

      <Card>
        <p className="mb-1 text-xs font-medium text-gray-500">Net P&amp;L</p>
        <p
          className={`text-2xl font-semibold ${
            netPnl > 0 ? 'text-green-600' : netPnl < 0 ? 'text-red-600' : 'text-gray-900'
          }`}
        >
          {formatCurrency(netPnl)}
        </p>
      </Card>

      <Card>
        <p className="mb-1 text-xs font-medium text-gray-500">Win Rate</p>
        <p className="text-2xl font-semibold text-gray-900">
          {formatPercent(winRate)}
        </p>
      </Card>
    </div>
  );
}
