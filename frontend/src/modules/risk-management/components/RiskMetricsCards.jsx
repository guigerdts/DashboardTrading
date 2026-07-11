import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatPercent, formatRatio } from '../../analytics/utils/formatters';

/**
 * Risk metric stat cards for streaks, holding time, Kelly, RoR, etc.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function RiskMetricsCards({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load risk metrics'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Risk Metrics</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
            >
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" className="mt-2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Empty state — no data or null
  if (!data) {
    return (
      <div>
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Risk Metrics</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          <Card title="Max Consecutive Wins">
            <p className="text-xl font-semibold text-gray-900">0</p>
          </Card>
          <Card title="Max Consecutive Losses">
            <p className="text-xl font-semibold text-gray-900">0</p>
          </Card>
          <Card title="Avg Holding Time">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
          <Card title="Avg Risk / Trade">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
          <Card title="Risk Utilization">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
          <Card title="Kelly Fraction">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
          <Card title="Risk of Ruin">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
          <Card title="Expectancy Adj.">
            <p className="text-xl font-semibold text-gray-900">—</p>
          </Card>
        </div>
      </div>
    );
  }

  const maxConWins = data.max_consecutive_wins ?? 0;
  const maxConLosses = data.max_consecutive_losses ?? 0;

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Risk Metrics</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <Card title="Max Consecutive Wins">
          <p className="text-xl font-semibold text-green-600">{maxConWins}</p>
        </Card>
        <Card title="Max Consecutive Losses">
          <p className="text-xl font-semibold text-red-600">{maxConLosses}</p>
        </Card>
        <Card title="Avg Holding Time">
          <p className="text-xl font-semibold text-gray-900">
            {data.avg_holding_time_hours != null
              ? `${data.avg_holding_time_hours.toFixed(1)}h`
              : '\u2014'}
          </p>
        </Card>
        <Card title="Avg Risk / Trade">
          <p className="text-xl font-semibold text-gray-900">
            {formatCurrency(data.avg_risk_per_trade)}
          </p>
        </Card>
        <Card title="Risk Utilization">
          <p className="text-xl font-semibold text-gray-900">
            {formatPercent(data.avg_risk_utilization)}
          </p>
        </Card>
        <Card title="Kelly Fraction">
          <p className="text-xl font-semibold text-gray-900">
            {formatRatio(data.kelly_fraction)}
          </p>
        </Card>
        <Card title="Risk of Ruin">
          <p className="text-xl font-semibold text-gray-900">
            {formatPercent(data.risk_of_ruin)}
          </p>
        </Card>
        <Card title="Expectancy Adj.">
          <p className="text-xl font-semibold text-gray-900">
            {formatRatio(data.expectancy_adjusted)}
          </p>
        </Card>
      </div>
    </div>
  );
}
