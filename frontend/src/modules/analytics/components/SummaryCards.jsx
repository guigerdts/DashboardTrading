import { SummaryCard } from './SummaryCard';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatPercent, formatRatio } from '../utils/formatters';

/**
 * Container for the 5 summary stat cards.
 * Handles loading (5 skeletons), empty (em dashes), error (retry), and success states.
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function SummaryCards({ data, isLoading, isError, error, onRetry }) {
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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
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

  // Empty state — no data or all values null
  if (!data) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <SummaryCard title="Net P&amp;L" value="\u2014" />
        <SummaryCard title="Win Rate" value="\u2014" />
        <SummaryCard title="Profit Factor" value="\u2014" />
        <SummaryCard title="Expectancy" value="\u2014" />
        <SummaryCard title="Max Drawdown" value="\u2014" />
      </div>
    );
  }

  const performance = data.performance || {};
  const risk = data.risk || {};
  const netPnl = performance.net_pnl ?? 0;
  const winRate = performance.win_rate ?? 0;
  const profitFactor = performance.profit_factor ?? 0;
  const expectancy = performance.expectancy ?? 0;
  const maxDrawdown = risk.max_drawdown ?? 0;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      <SummaryCard
        title="Net P&amp;L"
        value={formatCurrency(netPnl)}
        isPositive={netPnl > 0}
        isNegative={netPnl < 0}
      />
      <SummaryCard title="Win Rate" value={formatPercent(winRate)} />
      <SummaryCard title="Profit Factor" value={formatRatio(profitFactor)} />
      <SummaryCard
        title="Expectancy"
        value={formatCurrency(expectancy)}
        isPositive={expectancy > 0}
        isNegative={expectancy < 0}
      />
      <SummaryCard
        title="Max Drawdown"
        value={formatPercent(Math.abs(maxDrawdown))}
        isNegative={maxDrawdown < 0}
      />
    </div>
  );
}
