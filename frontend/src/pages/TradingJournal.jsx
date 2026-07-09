import { useNavigate } from 'react-router-dom';
import { ErrorBoundary } from '../shared/components/ErrorBoundary';
import { useJournalFilters } from '../modules/trades/hooks/useJournalFilters';
import { useJournalTrades } from '../modules/trades/hooks/useJournalTrades';
import { JournalFiltersBar } from '../modules/trades/components/JournalFiltersBar';
import { JournalSummaryCards } from '../modules/trades/components/JournalSummaryCards';
import { TradesTable } from '../modules/trades/components/TradesTable';
import { JournalPagination } from '../modules/trades/components/JournalPagination';

/**
 * Trading Journal page — orchestrator.
 *
 * Wires filter state (URL-synced), data fetching (React Query), and
 * presentational components together. Each section is wrapped in
 * ErrorBoundary so a crash in one never takes down the entire page.
 */
export default function TradingJournal() {
  const navigate = useNavigate();
  const { filters, setFilters, clearFilters, setPage } = useJournalFilters();
  const {
    listData,
    summaryData,
    isLoading,
    isError,
    error,
    isEmpty,
    isFilteredEmpty,
    refetch,
  } = useJournalTrades();

  const handleRowClick = (trade) => {
    navigate(`/trades/${trade.id}`);
  };

  const handleSort = (sortBy, sortDir) => {
    setFilters({ sortBy, sortDir });
  };

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Trading Journal</h1>

      {/* Summary cards */}
      <ErrorBoundary>
        <div className="mb-6">
          <JournalSummaryCards
            data={summaryData}
            isLoading={isLoading}
            isError={isError}
            error={error}
            onRetry={refetch}
          />
        </div>
      </ErrorBoundary>

      {/* Filters bar */}
      <ErrorBoundary>
        <div className="mb-6">
          <JournalFiltersBar
            filters={filters}
            onChange={setFilters}
            onClear={clearFilters}
          />
        </div>
      </ErrorBoundary>

      {/* Trades table */}
      <ErrorBoundary>
        <div className="mb-6">
          <TradesTable
            data={listData}
            isLoading={isLoading}
            isError={isError}
            error={error}
            onRetry={refetch}
            isEmpty={isEmpty}
            isFilteredEmpty={isFilteredEmpty}
            onClearFilters={clearFilters}
            onSort={handleSort}
            sortBy={filters.sortBy}
            sortDir={filters.sortDir}
            onRowClick={handleRowClick}
          />
        </div>
      </ErrorBoundary>

      {/* Pagination */}
      <ErrorBoundary>
        <JournalPagination
          page={filters.page}
          pages={listData?.pages ?? 1}
          total={listData?.total ?? 0}
          onPageChange={setPage}
        />
      </ErrorBoundary>
    </div>
  );
}
