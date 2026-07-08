import { useSummary } from '../hooks/useSummary';
import { useEquity } from '../hooks/useEquity';
import { useAssetBreakdown } from '../hooks/useAssetBreakdown';
import { useDirectionBreakdown } from '../hooks/useDirectionBreakdown';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';
import { FiltersBar } from '../components/FiltersBar';
import { SummaryCards } from '../components/SummaryCards';
import { EquityChart } from '../components/EquityChart';
import { AssetBreakdownTable } from '../components/AssetBreakdownTable';
import { DirectionBreakdown } from '../components/DirectionBreakdown';

/**
 * Dashboard page — orchestrator.
 *
 * Calls 4 parallel data hooks (summary, equity, asset breakdown, direction breakdown)
 * and wires their results into presentation components. Each data-driven widget is
 * wrapped in an ErrorBoundary so a crash in one never takes down the entire page.
 *
 * Filters are managed by useDashboardFilters (called inside each hook and FiltersBar)
 * and synced via URL search params — no direct filter call needed at this level.
 *
 * Loading, empty, error, and success states are handled per-widget by the components.
 */
export default function DashboardPage() {
  const summary = useSummary();
  const equity = useEquity();
  const assetBreakdown = useAssetBreakdown();
  const directionBreakdown = useDirectionBreakdown();

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Filters — self-contained, reads/writes URL search params */}
      <ErrorBoundary>
        <div className="mb-6">
          <FiltersBar />
        </div>
      </ErrorBoundary>

      {/* Summary cards — 5‑card grid */}
      <ErrorBoundary>
        <div className="mb-6">
          <SummaryCards
            data={summary.data}
            isLoading={summary.isLoading}
            isError={summary.isError}
            error={summary.error}
            onRetry={summary.refetch}
          />
        </div>
      </ErrorBoundary>

      {/* Equity chart — full width */}
      <ErrorBoundary>
        <div className="mb-6">
          <EquityChart
            data={equity.data}
            isLoading={equity.isLoading}
            isError={equity.isError}
            error={equity.error}
            onRetry={equity.refetch}
          />
        </div>
      </ErrorBoundary>

      {/* Two‑column breakdowns: asset table + direction comparison */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ErrorBoundary>
          <AssetBreakdownTable
            data={assetBreakdown.data}
            isLoading={assetBreakdown.isLoading}
            isError={assetBreakdown.isError}
            error={assetBreakdown.error}
            onRetry={assetBreakdown.refetch}
          />
        </ErrorBoundary>

        <ErrorBoundary>
          <DirectionBreakdown
            data={directionBreakdown.data}
            isLoading={directionBreakdown.isLoading}
            isError={directionBreakdown.isError}
            error={directionBreakdown.error}
            onRetry={directionBreakdown.refetch}
          />
        </ErrorBoundary>
      </div>
    </div>
  );
}
