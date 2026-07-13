import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { useRunComparison } from '../hooks/useStrategyLab';

const P_VALUE_THRESHOLDS = {
  high: 0.01,
  medium: 0.05,
};

function getConfidenceBadge(pValue) {
  if (pValue == null) return { label: 'Insufficient', style: 'bg-gray-100 text-gray-700' };
  if (pValue <= P_VALUE_THRESHOLDS.high) return { label: 'Very High', style: 'bg-green-100 text-green-700' };
  if (pValue <= P_VALUE_THRESHOLDS.medium) return { label: 'High', style: 'bg-blue-100 text-blue-700' };
  return { label: 'Low', style: 'bg-yellow-100 text-yellow-700' };
}

function getDeltaColor(delta) {
  if (delta == null) return 'text-gray-400';
  if (delta > 0) return 'text-green-600';
  if (delta < 0) return 'text-red-600';
  return 'text-gray-500';
}

function EffectSizeBar({ value, label }) {
  if (value == null) return <span className="text-xs text-gray-400">N/A</span>;

  const absVal = Math.abs(value);
  const clampedVal = Math.min(absVal, 1);
  const isPositive = value >= 0;

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            isPositive ? 'bg-green-400' : 'bg-red-400'
          }`}
          style={{ width: `${clampedVal * 100}%` }}
        />
      </div>
      <span className={`text-xs font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {value.toFixed(3)}
      </span>
    </div>
  );
}

function MetricRow({ label, runAValue, runBValue, delta, ci, pValue }) {
  const badge = getConfidenceBadge(pValue);
  const deltaColorClass = getDeltaColor(delta);

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-2 pr-3 text-sm font-medium text-gray-900">{label}</td>
      <td className="py-2 pr-3 text-sm text-gray-700 text-right">{runAValue ?? '—'}</td>
      <td className="py-2 pr-3 text-sm text-gray-700 text-right">{runBValue ?? '—'}</td>
      <td className={`py-2 pr-3 text-sm font-medium text-right ${deltaColorClass}`}>
        {delta != null ? `${delta > 0 ? '+' : ''}${delta.toFixed(4)}` : '—'}
      </td>
      <td className="py-2 pr-3 text-sm text-gray-600 text-right">
        {ci != null ? `${ci[0]?.toFixed(4) ?? '—'} – ${ci[1]?.toFixed(4) ?? '—'}` : '—'}
      </td>
      <td className="py-2 pr-3 text-sm text-right">
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${badge.style}`}>
          {pValue != null ? pValue.toFixed(4) : '—'} · {badge.label}
        </span>
      </td>
      <td className="py-2 text-sm">
        <EffectSizeBar value={delta} />
      </td>
    </tr>
  );
}

function ComparisonSkeleton() {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <Skeleton variant="text" width="240px" className="mb-4" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="mb-3 flex gap-4">
          <Skeleton variant="rect" height={20} width="14%" />
          <Skeleton variant="rect" height={20} width="10%" />
          <Skeleton variant="rect" height={20} width="10%" />
          <Skeleton variant="rect" height={20} width="10%" />
          <Skeleton variant="rect" height={20} width="14%" />
          <Skeleton variant="rect" height={20} width="16%" />
          <Skeleton variant="rect" height={20} width="12%" />
        </div>
      ))}
    </div>
  );
}

/**
 * Side-by-side comparison of two backtest runs.
 *
 * @param {{
 *   runId: string|number,
 *   baselineId: string|number,
 *   runALabel?: string,
 *   runBLabel?: string,
 * }} props
 */
export function ComparisonView({ runId, baselineId, runALabel = 'Run A', runBLabel = 'Run B' }) {
  const { data, isLoading, isError, error, refetch } = useRunComparison(runId, baselineId);

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load comparison data'}
        onRetry={refetch}
      />
    );
  }

  if (isLoading) {
    return <ComparisonSkeleton />;
  }

  if (!data || !data.comparison) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">No comparison data available</p>
      </div>
    );
  }

  const { comparison } = data;
  const metrics = comparison.metrics || [];

  // Summary stats at the top
  const summary = comparison.summary || {};

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-1 text-base font-semibold text-gray-900">Run Comparison</h3>
      <p className="mb-4 text-xs text-gray-400">
        Comparing {runALabel} (run #{runId}) vs {runBLabel} (baseline #{baselineId})
      </p>

      {/* Summary badges */}
      {summary.total_metrics != null && (
        <div className="mb-4 flex flex-wrap gap-4">
          <div className="rounded-md bg-gray-50 px-3 py-2 text-xs">
            <span className="text-gray-500">Metrics compared: </span>
            <span className="font-medium text-gray-900">{summary.total_metrics}</span>
          </div>
          {summary.significant_count != null && (
            <div className="rounded-md bg-green-50 px-3 py-2 text-xs">
              <span className="text-green-700">Significant: </span>
              <span className="font-medium text-green-800">{summary.significant_count}</span>
            </div>
          )}
          {summary.insufficient_count != null && (
            <div className="rounded-md bg-gray-50 px-3 py-2 text-xs">
              <span className="text-gray-500">Insufficient: </span>
              <span className="font-medium text-gray-700">{summary.insufficient_count}</span>
            </div>
          )}
        </div>
      )}

      {/* Global effect size */}
      {summary.global_effect_size != null && (
        <div className="mb-4 rounded-md bg-gray-50 p-3">
          <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
            Global Effect Size
          </span>
          <EffectSizeBar value={summary.global_effect_size} />
        </div>
      )}

      {/* Metrics comparison table */}
      {metrics.length === 0 ? (
        <div className="flex h-[80px] items-center justify-center">
          <p className="text-sm text-gray-400">No metrics available for comparison</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500">
                  Metric
                </th>
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500 text-right">
                  {runALabel}
                </th>
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500 text-right">
                  {runBLabel}
                </th>
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500 text-right">
                  Delta
                </th>
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500 text-right">
                  CI (95%)
                </th>
                <th className="pb-2 pr-3 text-xs font-medium uppercase tracking-wider text-gray-500 text-right">
                  P-value
                </th>
                <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                  Effect Size
                </th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m, i) => (
                <MetricRow
                  key={m.name || i}
                  label={m.name || `Metric #${i + 1}`}
                  runAValue={m.run_a}
                  runBValue={m.run_b}
                  delta={m.delta}
                  ci={m.confidence_interval}
                  pValue={m.p_value}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Color Legend */}
      <div className="mt-4 flex flex-wrap items-center gap-4 border-t border-gray-100 pt-3 text-xs text-gray-500">
        <span className="font-medium">Legend:</span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          Significant positive
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          Significant negative
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-gray-300" />
          Insufficient
        </span>
      </div>
    </div>
  );
}
