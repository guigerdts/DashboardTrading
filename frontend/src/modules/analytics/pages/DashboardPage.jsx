import { useSummary } from '../hooks/useSummary';
import { useEquity } from '../hooks/useEquity';
import { useAssetBreakdown } from '../hooks/useAssetBreakdown';
import { useDirectionBreakdown } from '../hooks/useDirectionBreakdown';
import { useBreakdownStrategies } from '../hooks/useBreakdownStrategies';
import { useBreakdownSetups } from '../hooks/useBreakdownSetups';
import { useBreakdownTags } from '../hooks/useBreakdownTags';
import { useBreakdownMistakes } from '../hooks/useBreakdownMistakes';
import { useRDistribution } from '../hooks/useRDistribution';
import { useHeatmap } from '../hooks/useHeatmap';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';
import { FiltersBar } from '../components/FiltersBar';
import { SummaryCards } from '../components/SummaryCards';
import { EquityChart } from '../components/EquityChart';
import { AssetBreakdownTable } from '../components/AssetBreakdownTable';
import { DirectionBreakdown } from '../components/DirectionBreakdown';
import { BreakdownTable } from '../components/BreakdownTable';
import { RHistogram } from '../components/RHistogram';
import { HeatmapChart } from '../components/HeatmapChart';

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
  const breakdownStrategies = useBreakdownStrategies();
  const breakdownSetups = useBreakdownSetups();
  const breakdownTags = useBreakdownTags();
  const breakdownMistakes = useBreakdownMistakes();
  const rDistribution = useRDistribution();
  const heatmap = useHeatmap();

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

      {/* Four breakdown tables in 2×2 grid */}
      <div className="mb-6 mt-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Breakdowns</h2>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <ErrorBoundary>
            <BreakdownTable title="Strategies" data={breakdownStrategies.data}
              isLoading={breakdownStrategies.isLoading} isError={breakdownStrategies.isError}
              error={breakdownStrategies.error} onRetry={breakdownStrategies.refetch} />
          </ErrorBoundary>
          <ErrorBoundary>
            <BreakdownTable title="Setups" data={breakdownSetups.data}
              isLoading={breakdownSetups.isLoading} isError={breakdownSetups.isError}
              error={breakdownSetups.error} onRetry={breakdownSetups.refetch} />
          </ErrorBoundary>
          <ErrorBoundary>
            <BreakdownTable title="Tags" data={breakdownTags.data}
              isLoading={breakdownTags.isLoading} isError={breakdownTags.isError}
              error={breakdownTags.error} onRetry={breakdownTags.refetch} />
          </ErrorBoundary>
          <ErrorBoundary>
            <BreakdownTable title="Mistakes" data={breakdownMistakes.data}
              isLoading={breakdownMistakes.isLoading} isError={breakdownMistakes.isError}
              error={breakdownMistakes.error} onRetry={breakdownMistakes.refetch} />
          </ErrorBoundary>
        </div>
      </div>

      {/* R Histogram */}
      <ErrorBoundary>
        <div className="mb-6">
          <RHistogram data={rDistribution.data}
            isLoading={rDistribution.isLoading} isError={rDistribution.isError}
            error={rDistribution.error} onRetry={rDistribution.refetch} />
        </div>
      </ErrorBoundary>

      {/* Heatmap */}
      <ErrorBoundary>
        <div className="mb-6">
          <HeatmapChart data={heatmap.data}
            isLoading={heatmap.isLoading} isError={heatmap.isError}
            error={heatmap.error} onRetry={heatmap.refetch} />
        </div>
      </ErrorBoundary>
    </div>
  );
}
