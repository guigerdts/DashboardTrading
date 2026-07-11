import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { CHART_COLORS } from '../utils/constants';

/**
 * R-multiple distribution histogram bar chart.
 * Data shape: { total_trades, buckets: [{ bucket: string, count: number }], trades_without_risk }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function RHistogram({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load R distribution'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="140px" className="mb-4" />
        <Skeleton variant="rect" height={300} />
      </div>
    );
  }

  const buckets = data?.buckets;

  if (!buckets || buckets.length === 0) {
    return (
      <div className="flex h-[350px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No R multiple data available</p>
      </div>
    );
  }

  const tradesWithoutRisk = data.trades_without_risk ?? 0;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">
        R Multiple Distribution
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={buckets} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis dataKey="bucket" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <Tooltip
            formatter={(value, _name) => [value, 'Trades']}
            labelFormatter={(label) => `R Bucket: ${label}`}
          />
          <Bar dataKey="count" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      {tradesWithoutRisk > 0 && (
        <p className="mt-2 text-xs text-gray-500">
          Trades without risk: {tradesWithoutRisk}
        </p>
      )}
    </div>
  );
}
