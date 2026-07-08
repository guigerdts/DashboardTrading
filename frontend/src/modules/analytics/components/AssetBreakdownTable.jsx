import { useMemo } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatPercent, formatRatio } from '../utils/formatters';

/**
 * Per-asset performance table — semantic HTML, sorted by net P&L descending.
 * Handles loading (3 skeleton rows), success, empty ("No trades found"), and error states.
 *
 * Expects data in the shape: { assets: [{ symbol, net_pnl, win_rate, trade_count, profit_factor }] }
 *
 * @param {{ data, isLoading, isError, error, onRetry?: () => void }} props
 */
export function AssetBreakdownTable({ data, isLoading, isError, error, onRetry }) {
  const assets = data?.assets;

  // Stable sort: always call hooks at the top level
  const sortedAssets = useMemo(() => {
    if (!assets || assets.length === 0) return [];
    return [...assets].sort((a, b) => (b.net_pnl ?? 0) - (a.net_pnl ?? 0));
  }, [assets]);

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load asset breakdown'}
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
            <Skeleton variant="rect" height={24} width="20%" />
            <Skeleton variant="rect" height={24} width="25%" />
            <Skeleton variant="rect" height={24} width="20%" />
            <Skeleton variant="rect" height={24} width="15%" />
            <Skeleton variant="rect" height={24} width="20%" />
          </div>
        ))}
      </div>
    );
  }

  if (!assets || assets.length === 0) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No trades found</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-4 text-sm font-medium text-gray-500">Asset Breakdown</h3>
      <div className="overflow-x-auto">
        <table className="w-full table-fixed text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="w-[18%] pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Symbol
              </th>
              <th className="w-[22%] pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Net P&amp;L
              </th>
              <th className="w-[20%] pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Win Rate
              </th>
              <th className="w-[18%] pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Trades
              </th>
              <th className="w-[22%] pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                Profit Factor
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedAssets.map((asset) => {
              const pnl = asset.net_pnl ?? 0;
              return (
                <tr
                  key={asset.symbol}
                  className="border-b border-gray-100 last:border-0"
                >
                  <td className="py-2 pr-2 font-medium text-gray-900">
                    {asset.symbol}
                  </td>
                  <td
                    className={`py-2 pr-2 ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : ''
                    }`}
                  >
                    {formatCurrency(pnl)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {formatPercent(asset.win_rate)}
                  </td>
                  <td className="py-2 pr-2 text-gray-700">
                    {asset.trade_count ?? '\u2014'}
                  </td>
                  <td className="py-2 text-gray-700">
                    {formatRatio(asset.profit_factor)}
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
