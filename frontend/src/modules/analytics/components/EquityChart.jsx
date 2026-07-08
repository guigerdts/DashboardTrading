import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatDate } from '../utils/formatters';
import { CHART_COLORS } from '../utils/constants';

/**
 * Equity curve chart using Recharts LineChart.
 * Handles loading (animated skeleton), success (gradient line), empty, and error states.
 *
 * Expects data in the shape: { equity_curve: [{ date: string, equity: number }] }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function EquityChart({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load equity chart'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="120px" className="mb-4" />
        <Skeleton variant="rect" height={300} />
      </div>
    );
  }

  const equityData = data?.equity_curve;

  if (!equityData || equityData.length === 0) {
    return (
      <div className="flex h-[350px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No trade data available</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">Equity Curve</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={equityData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS.gradientStart} stopOpacity={0.25} />
              <stop offset="95%" stopColor={CHART_COLORS.gradientEnd} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis
            dataKey="date"
            tickFormatter={(v) => formatDate(v)}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <YAxis
            tickFormatter={(v) => formatCurrency(v)}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <Tooltip
            formatter={(value) => [formatCurrency(value), 'Equity']}
            labelFormatter={(label) => formatDate(label)}
          />
          <Line
            type="monotone"
            dataKey="equity"
            stroke={CHART_COLORS.primary}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
