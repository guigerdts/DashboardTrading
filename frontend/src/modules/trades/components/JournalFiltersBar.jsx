import { useState, useEffect } from 'react';

/**
 * Filter controls for the Trading Journal.
 * Presentational — receives state and callbacks from parent hook.
 *
 * Search input uses local state for responsive feel while the parent
 * hook debounces the URL update (300ms).
 *
 * @param {{ filters, onChange: (partial: object) => void, onClear: () => void }} props
 */
export function JournalFiltersBar({ filters, onChange, onClear }) {
  // Local state for search input so it feels responsive during debounce
  const [searchInput, setSearchInput] = useState(filters.search || '');

  // Sync with URL-driven changes (e.g. clearFilters or back-button)
  useEffect(() => {
    setSearchInput(filters.search || '');
  }, [filters.search]);

  const hasActiveFilters = !!(
    filters.search ||
    filters.status ||
    filters.direction ||
    filters.dateFrom ||
    filters.dateTo
  );

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Search — debounced */}
      <div className="flex flex-col">
        <label
          htmlFor="journal-search"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          Search
        </label>
        <input
          id="journal-search"
          type="text"
          value={searchInput}
          onChange={(e) => {
            const val = e.target.value;
            setSearchInput(val);
            onChange({ search: val || null });
          }}
          placeholder="Search by ticket, symbol, notes..."
          className="w-48 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Status */}
      <div className="flex flex-col">
        <label
          htmlFor="journal-status"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          Status
        </label>
        <select
          id="journal-status"
          value={filters.status || ''}
          onChange={(e) => onChange({ status: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Direction */}
      <div className="flex flex-col">
        <label
          htmlFor="journal-direction"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          Direction
        </label>
        <select
          id="journal-direction"
          value={filters.direction || ''}
          onChange={(e) => onChange({ direction: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All</option>
          <option value="long">Long</option>
          <option value="short">Short</option>
        </select>
      </div>

      {/* Date from */}
      <div className="flex flex-col">
        <label
          htmlFor="journal-date-from"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          From
        </label>
        <input
          id="journal-date-from"
          type="date"
          value={filters.dateFrom || ''}
          onChange={(e) => onChange({ dateFrom: e.target.value || null })}
          aria-label="Date from"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Date to */}
      <div className="flex flex-col">
        <label
          htmlFor="journal-date-to"
          className="mb-1 text-xs font-medium text-gray-500"
        >
          To
        </label>
        <input
          id="journal-date-to"
          type="date"
          value={filters.dateTo || ''}
          onChange={(e) => onChange({ dateTo: e.target.value || null })}
          aria-label="Date to"
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Clear */}
      {hasActiveFilters && (
        <button
          onClick={onClear}
          className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
