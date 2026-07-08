import { useState, useEffect } from 'react';
import { useDashboardFilters } from '../hooks/useDashboardFilters';

/**
 * Filter controls for the analytics dashboard.
 * - account_id: text input with 300ms debounce via the hook
 * - date_from / date_to: date pickers with immediate updates
 * - Clear button: resets all filters
 *
 * Maintains local state for the text input to feel responsive while the
 * debounced URL update propagates through the hook.
 */
export function FiltersBar() {
  const { filters, setFilters, clearFilters } = useDashboardFilters();
  const [accountIdInput, setAccountIdInput] = useState(filters.accountId || '');

  // Sync URL-driven changes (e.g. clear or navigation) back to local state
  useEffect(() => {
    setAccountIdInput(filters.accountId || '');
  }, [filters.accountId]);

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Account ID — debounced */}
      <div className="flex flex-col">
        <label
          htmlFor="filter-account-id"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          Account ID
        </label>
        <input
          id="filter-account-id"
          type="text"
          value={accountIdInput}
          onChange={(e) => {
            const val = e.target.value;
            setAccountIdInput(val);
            setFilters({ accountId: val || null });
          }}
          placeholder="All accounts"
          className="w-36 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Date from — immediate */}
      <div className="flex flex-col">
        <label
          htmlFor="filter-date-from"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          From
        </label>
        <input
          id="filter-date-from"
          type="date"
          value={filters.dateFrom || ''}
          onChange={(e) => setFilters({ dateFrom: e.target.value || null })}
          aria-label="Date from"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Date to — immediate */}
      <div className="flex flex-col">
        <label
          htmlFor="filter-date-to"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          To
        </label>
        <input
          id="filter-date-to"
          type="date"
          value={filters.dateTo || ''}
          onChange={(e) => setFilters({ dateTo: e.target.value || null })}
          aria-label="Date to"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Clear */}
      <button
        onClick={clearFilters}
        className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
      >
        Clear
      </button>
    </div>
  );
}
