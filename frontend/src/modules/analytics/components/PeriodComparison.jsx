import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import {
  formatCurrency,
  formatPercent,
  formatRatio,
  formatNumber,
  formatDecimal,
} from '../utils/formatters';

const COMPARISON_FIELDS = [
  { key: 'trade_count', label: 'Trades', format: formatNumber },
  { key: 'net_pnl', label: 'Net P&L', format: formatCurrency },
  { key: 'gross_profit', label: 'Gross Profit', format: formatCurrency },
  { key: 'gross_loss', label: 'Gross Loss', format: formatCurrency },
  { key: 'win_rate', label: 'Win Rate', format: formatPercent },
  { key: 'profit_factor', label: 'Profit Factor', format: formatRatio },
  { key: 'expectancy', label: 'Expectancy', format: (v) => (v != null ? v.toFixed(2) : '\u2014') },
  { key: 'avg_r_multiple', label: 'Avg R', format: formatDecimal },
];

/**
 * Period comparison — side-by-side A vs B with delta and delta_percent columns.
 *
 * Data shape: { period_a: PerformanceByPeriodRecord, period_b: PerformanceByPeriodRecord,
 *   delta: PerformanceByPeriodRecord, delta_percent: PerformanceByPeriodRecord }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function PeriodComparison({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load period comparison'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="160px" className="mb-4" />
        <Skeleton variant="rect" height={300} />
      </div>
    );
  }

  if (!data || !data.period_a || !data.period_b) {
    return (
      <div className="flex h-[250px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No comparison data available</p>
      </div>
    );
  }

  const { period_a, period_b, delta, delta_percent } = data;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">Period Comparison</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-xs font-medium uppercase text-gray-400">
              <th className="py-2 pr-3">Metric</th>
              <th className="py-2 pr-3">Period A</th>
              <th className="py-2 pr-3">Period B</th>
              <th className="py-2 pr-3">Delta</th>
              <th className="py-2 pr-3">Delta %</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_FIELDS.map((field) => {
              const aVal = period_a[field.key];
              const bVal = period_b[field.key];
              const dVal = delta?.[field.key];
              const dpVal = delta_percent?.[field.key];

              const isPnl = field.key === 'net_pnl' || field.key === 'gross_profit';
              const isLoss = field.key === 'gross_loss';

              return (
                <tr key={field.key} className="border-b border-gray-100">
                  <td className="py-2 pr-3 font-medium text-gray-900">{field.label}</td>
                  <td className={`py-2 pr-3 ${isPnl && aVal >= 0 ? 'text-green-600' : ''} ${isPnl && aVal < 0 ? 'text-red-600' : ''} ${isLoss ? 'text-red-600' : ''}`}>
                    {field.format(aVal)}
                  </td>
                  <td className={`py-2 pr-3 ${isPnl && bVal >= 0 ? 'text-green-600' : ''} ${isPnl && bVal < 0 ? 'text-red-600' : ''} ${isLoss ? 'text-red-600' : ''}`}>
                    {field.format(bVal)}
                  </td>
                  <td className={`py-2 pr-3 ${dVal != null && dVal > 0 ? 'text-green-600' : ''} ${dVal != null && dVal < 0 ? 'text-red-600' : ''} ${dVal == null ? 'text-gray-400' : ''}`}>
                    {dVal != null ? field.format(dVal) : '\u2014'}
                  </td>
                  <td className={`py-2 pr-3 ${dpVal != null && dpVal > 0 ? 'text-green-600' : ''} ${dpVal != null && dpVal < 0 ? 'text-red-600' : ''} ${dpVal == null ? 'text-gray-400' : ''}`}>
                    {dpVal != null ? `${dpVal.toFixed(2)}%` : '\u2014'}
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
