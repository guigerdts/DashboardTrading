import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import {
  formatCurrency,
  formatPercent,
  formatRatio,
  formatNumber,
  formatDecimal,
} from '../utils/formatters';

const PERIOD_OPTIONS = [
  { value: 'month', label: 'Monthly' },
  { value: 'quarter', label: 'Quarterly' },
  { value: 'year', label: 'Yearly' },
];

/**
 * Performance by period table with period toggle.
 *
 * Data shape: { records: [{ period, trade_count, net_pnl, gross_profit,
 *   gross_loss, win_rate, profit_factor, expectancy, avg_r_multiple }] }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void, period?: string,
 *   onPeriodChange?: (period: string) => void }} props
 */
export function PerformanceByPeriod({
  data,
  isLoading,
  isError,
  error,
  onRetry,
  period = 'month',
  onPeriodChange,
}) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load performance by period'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="160px" className="mb-4" />
        <Skeleton variant="rect" height={250} />
      </div>
    );
  }

  const records = data?.records;

  if (!records || records.length === 0) {
    return (
      <div className="flex h-[250px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No performance data available</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">Performance by Period</h3>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onPeriodChange?.(opt.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                period === opt.value
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-400">
              <th className="py-2 pr-3">Period</th>
              <th className="py-2 pr-3">Trades</th>
              <th className="py-2 pr-3">Net P&L</th>
              <th className="py-2 pr-3">Win Rate</th>
              <th className="py-2 pr-3">Profit Factor</th>
              <th className="py-2 pr-3">Expectancy</th>
              <th className="py-2 pr-3">Avg R</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.period} className="border-b border-gray-100">
                <td className="py-2 pr-3 font-medium text-gray-900">{record.period}</td>
                <td className="py-2 pr-3 text-gray-700">{formatNumber(record.trade_count)}</td>
                <td className={`py-2 pr-3 ${record.net_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(record.net_pnl)}
                </td>
                <td className="py-2 pr-3 text-gray-700">{formatPercent(record.win_rate)}</td>
                <td className="py-2 pr-3 text-gray-700">
                  {record.profit_factor != null ? formatRatio(record.profit_factor) : '\u2014'}
                </td>
                <td className="py-2 pr-3 text-gray-700">{formatDecimal(record.expectancy)}</td>
                <td className="py-2 pr-3 text-gray-700">
                  {record.avg_r_multiple != null ? formatDecimal(record.avg_r_multiple) : '\u2014'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
