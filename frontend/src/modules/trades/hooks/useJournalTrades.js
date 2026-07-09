import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useJournalFilters } from './useJournalFilters';
import { tradesApi } from '../api/trades';

/**
 * Check whether any filter (besides pagination/sort) is actively set.
 */
function isFiltered(filters) {
  return !!(
    filters.search ||
    filters.status ||
    filters.direction ||
    filters.accountId ||
    filters.assetId ||
    filters.dateFrom ||
    filters.dateTo
  );
}

/**
 * React Query hook that fetches both the paginated trades list and the
 * aggregated summary with the SAME filters object.
 *
 * 5-state machine for consumers:
 * | State           | Detection                                     |
 * |-----------------|-----------------------------------------------|
 * | loading         | isLoading (first load, no cached data)        |
 * | error           | isError (either query failed)                 |
 * | empty           | list total === 0 AND no filters active        |
 * | filtered-empty  | list total === 0 AND filters are active       |
 * | success         | list total > 0                                |
 *
 * @returns {{ listData, summaryData, isLoading, isError, error, isFetching, isEmpty, isFilteredEmpty, refetch }}
 */
export function useJournalTrades() {
  const { filters, setFilters } = useJournalFilters();

  // ── List query (paginated) ──────────────────────────────────────────
  const listQuery = useQuery({
    queryKey: [
      'trades',
      'list',
      {
        accountId: filters.accountId,
        assetId: filters.assetId,
        direction: filters.direction,
        status: filters.status,
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
        search: filters.search,
        sortBy: filters.sortBy,
        sortDir: filters.sortDir,
        page: filters.page,
        pageSize: filters.pageSize,
      },
    ],
    queryFn: ({ signal }) => tradesApi.list(filters, { signal }),
    staleTime: 30_000,
    keepPreviousData: true,
  });

  // ── Summary query (no pagination/sort in key) ──────────────────────
  const summaryQuery = useQuery({
    queryKey: [
      'trades',
      'summary',
      {
        accountId: filters.accountId,
        assetId: filters.assetId,
        direction: filters.direction,
        status: filters.status,
        dateFrom: filters.dateFrom,
        dateTo: filters.dateTo,
        search: filters.search,
      },
    ],
    queryFn: ({ signal }) => tradesApi.summary(filters, { signal }),
    staleTime: 30_000,
  });

  // ── REF-04: Page clamping ──────────────────────────────────────────
  // If the API returns fewer pages than the current page, reset to 1.
  const prevPagesRef = useRef(null);
  useEffect(() => {
    const pages = listQuery.data?.pages;
    if (pages !== undefined && pages !== null && pages !== prevPagesRef.current) {
      if (filters.page > pages) {
        setFilters({ page: 1 });
      }
      prevPagesRef.current = pages;
    }
  }, [listQuery.data?.pages, filters.page, setFilters]);

  // ── Derived state ──────────────────────────────────────────────────
  const isLoading = listQuery.isLoading || summaryQuery.isLoading;
  const isError = listQuery.isError || summaryQuery.isError;
  const error = listQuery.error || summaryQuery.error;
  const isFetching = listQuery.isFetching || summaryQuery.isFetching;

  const listTotal = listQuery.data?.total ?? 0;
  const isEmpty = listQuery.isSuccess && listTotal === 0 && !isFiltered(filters);
  const isFilteredEmpty = listQuery.isSuccess && listTotal === 0 && isFiltered(filters);

  return {
    listData: listQuery.data ?? null,
    summaryData: summaryQuery.data ?? null,
    isLoading,
    isError,
    error,
    isFetching,
    isEmpty,
    isFilteredEmpty,
    refetch: () => {
      listQuery.refetch();
      summaryQuery.refetch();
    },
  };
}
