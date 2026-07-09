import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

/**
 * URL-synced filter state for the Trading Journal.
 *
 * - Reads initial values from URL searchParams on mount.
 * - Writes updates back to the URL (replace, no navigation).
 * - Text inputs (search) are debounced at 300ms (REF-01).
 * - Select/date/page changes update the URL immediately.
 * - Changing any filter resets page to 1 (REQ-SPEC-01), except page itself.
 *
 * @returns {{ filters, setFilters, clearFilters, setPage }}
 */
export function useJournalFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Derive current filter values from the URL
  const filters = useMemo(() => {
    const rawAccountId = searchParams.get('account_id');
    const accountIdNum = rawAccountId ? parseInt(rawAccountId, 10) : null;
    const rawAssetId = searchParams.get('asset_id');
    const assetIdNum = rawAssetId ? parseInt(rawAssetId, 10) : null;
    return {
      search: searchParams.get('search') || null,
      status: searchParams.get('status') || null,
      direction: searchParams.get('direction') || null,
      accountId: accountIdNum !== null && !isNaN(accountIdNum) ? accountIdNum : null,
      assetId: assetIdNum !== null && !isNaN(assetIdNum) ? assetIdNum : null,
      dateFrom: searchParams.get('date_from') || null,
      dateTo: searchParams.get('date_to') || null,
      sortBy: searchParams.get('sort_by') || 'entry_datetime',
      sortDir: searchParams.get('sort_dir') || 'desc',
      page: parseInt(searchParams.get('page') || '1', 10),
      pageSize: parseInt(searchParams.get('page_size') || '20', 10),
    };
  }, [searchParams]);

  // Debounce refs for text inputs (search)
  const debounceRefs = useRef({});

  // Cleanup debounce timers on unmount
  useEffect(() => {
    return () => {
      Object.values(debounceRefs.current).forEach((t) => clearTimeout(t));
    };
  }, []);

  const updateURL = useCallback(
    (partial) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);

          // Filters that reset page to 1 when changed
          const pageResettingFilters = [
            'search',
            'status',
            'direction',
            'accountId',
            'assetId',
            'dateFrom',
            'dateTo',
          ];
          const shouldResetPage =
            !('page' in partial) &&
            Object.keys(partial).some((k) => pageResettingFilters.includes(k));

          for (const [key, value] of Object.entries(partial)) {
            const paramName = camelToSnake(key);
            if (value != null && value !== '') {
              next.set(paramName, String(value));
            } else {
              next.delete(paramName);
            }
          }

          if (shouldResetPage) {
            next.set('page', '1');
          }

          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const setFilters = useCallback(
    (partial) => {
      // Debounce text inputs (search)
      const debounceKeys = ['search'];
      const needsDebounce = Object.keys(partial).some((k) => debounceKeys.includes(k));

      if (needsDebounce) {
        for (const key of Object.keys(partial)) {
          if (debounceKeys.includes(key)) {
            if (debounceRefs.current[key]) clearTimeout(debounceRefs.current[key]);
            debounceRefs.current[key] = setTimeout(() => updateURL({ [key]: partial[key] }), 300);
          }
        }
      } else {
        // Immediate update for selects, dates, sort, page
        updateURL(partial);
      }
    },
    [updateURL],
  );

  const clearFilters = useCallback(() => {
    Object.values(debounceRefs.current).forEach((t) => clearTimeout(t));
    debounceRefs.current = {};
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const setPage = useCallback((page) => setFilters({ page }), [setFilters]);

  return { filters, setFilters, clearFilters, setPage };
}

/** Convert camelCase to snake_case for URL params */
function camelToSnake(str) {
  return str.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase());
}
