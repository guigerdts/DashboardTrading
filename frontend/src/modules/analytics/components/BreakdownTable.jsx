import { useMemo } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import {
  formatCurrency,
  formatPercent,
  formatNumber,
  formatRatio,
} from '../utils/formatters';

/**
 * Reusable breakdown table for strategies, setups, tags, mistakes.
 * Data shape: { items: [{ id, name, trade_count, win_rate, net_pnl, gross_profit,
 *   gross_loss, profit_factor, expectancy, avg_win, avg_loss }] }
 * Sorted by net_pnl descending.
 *
 * @param {{ title: string, data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function BreakdownTable({ title, data, isLoading, isError, error, onRetry }) {
  const items = data?.items;

  const sortedItems = useMemo(() => {
    if (!items || items.length === 0) return [];
    return [...items].sort((a, b) => (b.net_pnl ?? 0) - (a.net_pnl ?? 0));
  }, [items]);

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || `Failed to load ${title}`}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="140px" className="mb-4" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="mb-3 flex gap-4">
            <Skeleton variant="rect" height={24} width="16%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="12%" />
            <Skeleton variant="rect" height={24} width="12%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="14%" />
          </div>
        ))}
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No data</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Name
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Net P&amp;L
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Win Rate
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Trades
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Profit Factor
              </th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Avg Win
              </th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Avg Loss
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedItems.map((item) => {
              const pnl = item.net_pnl ?? 0;
              return (
                <tr
                  key={item.id}
                  className="border-b border-gray-100 last:border-0"
                >
                  <td className="py-2 pr-2 font-medium text-gray-900">
                    {item.name}
                  </td>
                  <td
                    className={`py-2 pr-2 ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : ''
                    }`}
                  >
                    {formatCurrency(pnl)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatPercent(item.win_rate)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatNumber(item.trade_count)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatRatio(item.profit_factor)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatCurrency(item.avg_win)}
                  </td>
                  <td className="py-2 text-gray-700">
                    {formatCurrency(item.avg_loss)}
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
