import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * URL-synced filter state for the analytics dashboard.
 *
 * - Reads initial values from URL searchParams on mount.
 * - Writes updates back to the URL (replace, no navigation).
 * - `accountId` changes are debounced at 300ms to avoid API spam on rapid typing.
 * - Date changes (`dateFrom`, `dateTo`) update the URL immediately.
 *
 * @returns {{ filters, setFilters, clearFilters }}
 */
export function useDashboardFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Derive current filter values from the URL — drives all queries
  const filters = useMemo(
    () => {
      const rawAccountId = searchParams.get('account_id');
      const accountIdNum = rawAccountId ? parseInt(rawAccountId, 10) : null;
      return {
        accountId: accountIdNum !== null && !isNaN(accountIdNum) ? accountIdNum : null,
        dateFrom: searchParams.get('date_from') || null,
        dateTo: searchParams.get('date_to') || null,
      };
    },
    [searchParams],
  );

  // Debounce timer for accountId text input
  const debounceRef = useRef(null);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const updateURL = useCallback(
    (partial) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          if ('accountId' in partial) {
            if (partial.accountId) next.set('account_id', partial.accountId);
            else next.delete('account_id');
          }
          if ('dateFrom' in partial) {
            if (partial.dateFrom) next.set('date_from', partial.dateFrom);
            else next.delete('date_from');
          }
          if ('dateTo' in partial) {
            if (partial.dateTo) next.set('date_to', partial.dateTo);
            else next.delete('date_to');
          }

          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  /**
   * Update one or more filters.
   * - `accountId` → debounced at 300ms (for text input)
   * - `dateFrom` / `dateTo` → updated immediately
   */
  const setFilters = useCallback(
    (partial) => {
      if ('accountId' in partial) {
        // Cancel any pending debounce and restart
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          updateURL(partial);
        }, 300);
      } else {
        // Date fields update immediately
        if (debounceRef.current) clearTimeout(debounceRef.current);
        updateURL(partial);
      }
    },
    [updateURL],
  );

  /** Clear all filters — removes all analytics params from the URL */
  const clearFilters = useCallback(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  return { filters, setFilters, clearFilters };
}
