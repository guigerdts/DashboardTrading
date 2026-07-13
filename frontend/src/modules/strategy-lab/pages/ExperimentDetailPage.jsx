import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ExperimentDetail } from '../components/ExperimentDetail';
import { ComparisonView } from '../components/ComparisonView';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';

/**
 * Experiment detail page — shows metadata, runs, and comparison mode.
 */
export default function ExperimentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [runId, setRunId] = useState(null);
  const [baselineId, setBaselineId] = useState(null);

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => navigate('/lab/experiments')}
          className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
        >
          &larr; Back to experiments
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Experiment Detail</h1>
      </div>

      <ErrorBoundary>
        <ExperimentDetail experimentId={id} />
      </ErrorBoundary>

      {/* Comparison mode */}
      <div className="mt-8">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <h2 className="text-base font-semibold text-gray-900">Compare Runs</h2>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-gray-500" htmlFor="cmp-run">Run:</label>
            <input
              id="cmp-run"
              type="number"
              placeholder="Run ID"
              value={runId ?? ''}
              onChange={(e) => setRunId(e.target.value ? Number(e.target.value) : null)}
              className="w-24 rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
            />
            <label className="text-gray-500" htmlFor="cmp-baseline">Baseline:</label>
            <input
              id="cmp-baseline"
              type="number"
              placeholder="Baseline ID"
              value={baselineId ?? ''}
              onChange={(e) => setBaselineId(e.target.value ? Number(e.target.value) : null)}
              className="w-24 rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>

        {runId && baselineId ? (
          <ErrorBoundary>
            <ComparisonView
              runId={runId}
              baselineId={baselineId}
              runALabel="Run"
              runBLabel="Baseline"
            />
          </ErrorBoundary>
        ) : (
          <div className="flex h-[80px] items-center justify-center rounded-lg border border-dashed border-gray-200 bg-white shadow-sm">
            <p className="text-sm text-gray-400">
              Enter a Run ID and Baseline ID to view comparison
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
