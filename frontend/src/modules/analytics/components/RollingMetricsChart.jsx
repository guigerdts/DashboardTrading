import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatRatio, formatPercent } from '../utils/formatters';
import { CHART_COLORS } from '../utils/constants';

const LINE_COLORS = {
  win_rate: CHART_COLORS.primary,
  profit_factor: '#8b5cf6',
  expectancy: CHART_COLORS.negative,
  avg_r_multiple: CHART_COLORS.neutral,
};

/**
 * Rolling metrics line chart — win_rate, profit_factor, expectancy, avg_r
 * over trade index.
 *
 * Data shape: { window_size, points: [{ index, win_rate, profit_factor,
 *   expectancy, avg_r_multiple, trade_count }] }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function RollingMetricsChart({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load rolling metrics'}
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

  const points = data?.points;

  if (!points || points.length === 0) {
    return (
      <div className="flex h-[350px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">Insufficient data</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">Rolling Metrics</h3>
      <p className="mb-2 text-xs text-gray-400">
        Window size: {data.window_size} trades &middot; {points.length} data points
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={points} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis
            dataKey="index"
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
            label={{ value: 'Trade Index', position: 'insideBottomRight', offset: -5, style: { fontSize: 11, fill: '#9ca3af' } }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <Tooltip
            formatter={(value, name) => {
              switch (name) {
                case 'win_rate':
                  return [formatPercent(value), 'Win Rate'];
                case 'profit_factor':
                  return [formatRatio(value), 'Profit Factor'];
                case 'expectancy':
                  return [formatRatio(value), 'Expectancy'];
                case 'avg_r_multiple':
                  return [formatRatio(value), 'Avg R'];
                default:
                  return [value, name];
              }
            }}
            labelFormatter={(label) => `Trade #${label}`}
          />
          <Legend
            formatter={(value) => {
              const labels = {
                win_rate: 'Win Rate',
                profit_factor: 'Profit Factor',
                expectancy: 'Expectancy',
                avg_r_multiple: 'Avg R',
              };
              return labels[value] || value;
            }}
          />
          <Line
            type="monotone"
            dataKey="win_rate"
            stroke={LINE_COLORS.win_rate}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="profit_factor"
            stroke={LINE_COLORS.profit_factor}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="expectancy"
            stroke={LINE_COLORS.expectancy}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
          <Line
            type="monotone"
            dataKey="avg_r_multiple"
            stroke={LINE_COLORS.avg_r_multiple}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
