import { Fragment, useMemo } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency } from '../utils/formatters';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const HOUR_LABELS = Array.from({ length: 24 }, (_, i) =>
  String(i).padStart(2, '0'),
);

/**
 * Get a Tailwind background class based on trade count relative to max.
 * @param {number} count
 * @param {number} maxCount
 * @returns {string}
 */
function getBgClass(count, maxCount) {
  if (count === 0) return 'bg-gray-50';
  const ratio = count / maxCount;
  if (ratio > 0.75) return 'bg-green-700';
  if (ratio > 0.5) return 'bg-green-500';
  if (ratio > 0.25) return 'bg-green-300';
  return 'bg-green-100';
}

/**
 * Day × hour trading activity heatmap — pure CSS grid, no chart library.
 * Data shape: { total_trades, cells: [{ day: number (0-6), hour: number (0-23),
 *   trade_count: number, net_pnl: number }] }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function HeatmapChart({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load heatmap'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="120px" className="mb-4" />
        <Skeleton variant="rect" height={400} />
      </div>
    );
  }

  const cells = data?.cells;

  if (!cells || cells.length === 0) {
    return (
      <div className="flex h-[450px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No heatmap data available</p>
      </div>
    );
  }

  // Build a lookup: cellMap[day][hour] = { trade_count, net_pnl }
  const { cellMap, maxCount } = useMemo(() => {
    const map = Array.from({ length: 7 }, () => Array(24).fill(null));
    let mx = 0;
    for (const cell of cells) {
      if (cell.day >= 0 && cell.day < 7 && cell.hour >= 0 && cell.hour < 24) {
        map[cell.day][cell.hour] = {
          trade_count: cell.trade_count ?? 0,
          net_pnl: cell.net_pnl ?? 0,
        };
        mx = Math.max(mx, cell.trade_count ?? 0);
      }
    }
    return { cellMap: map, maxCount: mx };
  }, [cells]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">Trading Heatmap</h3>
      <div className="overflow-x-auto">
        <div
          className="grid gap-[2px]"
          style={{
            gridTemplateColumns: '54px repeat(24, minmax(28px, 1fr))',
          }}
        >
          {/* Corner cell */}
          <div />

          {/* Hour header row */}
          {HOUR_LABELS.map((hour) => (
            <div
              key={hour}
              className="text-center text-[10px] font-medium text-gray-400"
            >
              {hour}
            </div>
          ))}

          {/* Day rows */}
          {DAY_LABELS.map((dayLabel, dayIdx) => (
            <Fragment key={dayLabel}>
              <div
                className="flex items-center pr-2 text-[10px] font-medium text-gray-400"
              >
                {dayLabel}
              </div>
              {Array.from({ length: 24 }, (_, hourIdx) => {
                const cell = cellMap[dayIdx][hourIdx];
                const count = cell?.trade_count ?? 0;
                return (
                  <div
                    key={`${dayIdx}-${hourIdx}`}
                    className={`flex items-center justify-center rounded text-[10px] ${getBgClass(count, maxCount)} ${count > 0 ? 'text-white' : 'text-gray-400'}`}
                    style={{ aspectRatio: '1', minHeight: 28 }}
                    title={
                      count > 0
                        ? `${dayLabel} ${HOUR_LABELS[hourIdx]}:00 — ${count} trade${count !== 1 ? 's' : ''}, ${formatCurrency(cell.net_pnl)}`
                        : undefined
                    }
                  >
                    {count > 0 ? count : ''}
                  </div>
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}
