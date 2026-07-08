import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatPercent, formatRatio } from '../utils/formatters';

/**
 * Long vs Short comparison — two-column layout.
 * Handles loading (2 skeleton columns), success, empty, and error states.
 *
 * Expects data in the shape: { long: PerformanceMetrics, short: PerformanceMetrics }
 * where PerformanceMetrics = { net_pnl, win_rate, profit_factor, trade_count, expectancy }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function DirectionBreakdown({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load direction breakdown'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {['Long', 'Short'].map((dir) => (
          <div
            key={dir}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <Skeleton variant="text" width="60px" className="mb-4" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} variant="text" width="80%" className="mb-2" />
            ))}
          </div>
        ))}
      </div>
    );
  }

  if (!data || (!data.long && !data.short)) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No direction data available</p>
      </div>
    );
  }

  const renderColumn = (label, dirData) => {
    if (!dirData) {
      return (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-sm font-medium text-gray-500">{label}</h3>
          <p className="text-sm text-gray-400">No data</p>
        </div>
      );
    }

    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="mb-4 text-sm font-medium text-gray-500">{label}</h3>
        <div className="space-y-3">
          <MetricRow
            label="Net P&amp;L"
            value={formatCurrency(dirData.net_pnl)}
            isPositive={dirData.net_pnl > 0}
            isNegative={dirData.net_pnl < 0}
          />
          <MetricRow
            label="Win Rate"
            value={formatPercent(dirData.win_rate)}
          />
          <MetricRow
            label="Profit Factor"
            value={formatRatio(dirData.profit_factor)}
          />
          <MetricRow
            label="Trades"
            value={dirData.trade_count ?? '\u2014'}
          />
          <MetricRow
            label="Expectancy"
            value={formatCurrency(dirData.expectancy)}
            isPositive={dirData.expectancy > 0}
            isNegative={dirData.expectancy < 0}
          />
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {renderColumn('Long', data.long)}
      {renderColumn('Short', data.short)}
    </div>
  );
}

/** Single metric row inside a direction column */
function MetricRow({ label, value, isPositive, isNegative }) {
  const colorClass =
    isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-900';

  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-sm font-medium ${colorClass}`}>{value}</span>
    </div>
  );
}
