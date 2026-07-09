import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatDate } from '../../analytics/utils/formatters';

const SORTABLE_COLUMNS = ['broker_ticket', 'symbol', 'entry_datetime', 'exit_datetime', 'net_pnl'];

const COLUMNS = [
  { key: 'broker_ticket', label: 'Ticket', sortable: true },
  { key: 'symbol', label: 'Symbol', sortable: true },
  { key: 'direction', label: 'Direction', sortable: false },
  { key: 'entry_datetime', label: 'Entry Date', sortable: true },
  { key: 'exit_datetime', label: 'Exit Date', sortable: true },
  { key: 'net_pnl', label: 'P&L', sortable: true },
  { key: 'status', label: 'Status', sortable: false },
  { key: 'has_review', label: '', sortable: false },
];

/**
 * Trades table with 5 visual states: loading, error, empty, filtered-empty, success.
 *
 * @param {{
 *   data: { items?: Array, total?: number },
 *   isLoading: boolean,
 *   isError: boolean,
 *   error: Error | null,
 *   onRetry: () => void,
 *   isEmpty: boolean,
 *   isFilteredEmpty: boolean,
 *   onClearFilters: () => void,
 *   onSort: (sortBy: string, sortDir: string) => void,
 *   sortBy: string,
 *   sortDir: string,
 *   onRowClick?: (trade: object) => void,
 * }} props
 */
export function TradesTable({
  data,
  isLoading,
  isError,
  error,
  onRetry,
  isEmpty,
  isFilteredEmpty,
  onClearFilters,
  onSort,
  sortBy,
  sortDir,
  onRowClick,
}) {
  // ── Error state ───────────────────────────────────────────────────
  if (isError) {
    return (
      <Card>
        <ErrorFallback
          message={error?.message || 'Failed to load trades'}
          onRetry={onRetry}
        />
      </Card>
    );
  }

  // ── Loading state ─────────────────────────────────────────────────
  if (isLoading) {
    return (
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                {COLUMNS.map((col) => (
                  <th key={col.key} className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 5 }).map((_, rowIdx) => (
                <tr key={rowIdx} className="border-b border-gray-100 last:border-0">
                  {COLUMNS.map((col) => (
                    <td key={col.key} className="py-3 pr-2">
                      <Skeleton variant="text" width={col.key === 'symbol' ? '60%' : '80%'} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    );
  }

  // ── Absolute empty state (no trades exist at all) ─────────────────
  if (isEmpty) {
    return (
      <Card>
        <div className="flex h-[200px] flex-col items-center justify-center text-center">
          <p className="text-gray-400">
            No trades yet. Import your first trades to get started.
          </p>
        </div>
      </Card>
    );
  }

  // ── Filtered-empty state (trades exist, none match filters) ──────
  if (isFilteredEmpty) {
    return (
      <Card>
        <div className="flex h-[200px] flex-col items-center justify-center text-center">
          <p className="mb-3 text-gray-400">
            No trades match your filters. Try adjusting your search or filter criteria.
          </p>
          <button
            onClick={onClearFilters}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
          >
            Clear filters
          </button>
        </div>
      </Card>
    );
  }

  // ── Success state ─────────────────────────────────────────────────
  const items = data?.items ?? [];

  const handleSortClick = (column) => {
    if (!SORTABLE_COLUMNS.includes(column)) return;
    if (sortBy === column) {
      // Toggle direction: DESC → ASC → DESC
      onSort(column, sortDir === 'desc' ? 'asc' : 'desc');
    } else {
      // New sort column → start with DESC
      onSort(column, 'desc');
    }
  };

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              {COLUMNS.map((col) => {
                const isSortable = col.sortable;
                const isActive = sortBy === col.key;
                return (
                  <th
                    key={col.key}
                    className={`pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500 ${
                      isSortable ? 'cursor-pointer select-none hover:text-gray-700' : ''
                    }`}
                    onClick={() => handleSortClick(col.key)}
                    aria-sort={
                      isActive ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined
                    }
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {isActive && (
                        <span className="text-blue-600">
                          {sortDir === 'asc' ? '\u25B2' : '\u25BC'}
                        </span>
                      )}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {items.map((trade) => {
              const pnl = trade.net_pnl ?? 0;
              return (
                <tr
                  key={trade.id}
                  onClick={() => onRowClick?.(trade)}
                  className="cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-50 last:border-0"
                >
                  <td className="py-3 pr-2 font-mono text-xs text-gray-600">
                    {trade.broker_ticket ?? '\u2014'}
                  </td>
                  <td className="py-3 pr-2 font-medium text-gray-900">
                    {trade.asset_symbol ?? '\u2014'}
                  </td>
                  <td className="py-3 pr-2 text-gray-700">
                    {trade.direction === 'long' ? (
                      <span className="text-green-600">Long \u2191</span>
                    ) : trade.direction === 'short' ? (
                      <span className="text-red-600">Short \u2193</span>
                    ) : (
                      '\u2014'
                    )}
                  </td>
                  <td className="py-3 pr-2 text-gray-700">
                    {formatDate(trade.entry_datetime)}
                  </td>
                  <td className="py-3 pr-2 text-gray-700">
                    {trade.exit_datetime ? formatDate(trade.exit_datetime) : '\u2014'}
                  </td>
                  <td
                    className={`py-3 pr-2 font-medium ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : ''
                    }`}
                  >
                    {formatCurrency(pnl)}
                  </td>
                  <td className="py-3 pr-2">
                    {trade.status === 'closed' ? (
                      <span className="inline-flex rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        Closed
                      </span>
                    ) : trade.status === 'open' ? (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                        Open
                      </span>
                    ) : (
                      '\u2014'
                    )}
                  </td>
                  <td className="py-3 pr-2 text-center">
                    {trade.has_review ? (
                      <span className="text-xs text-yellow-600" title="Has review">\u2605</span>
                    ) : (
                      <span className="text-xs text-gray-300">\u2606</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
