import { useState } from 'react';
import { useEdgeRankings, useGenerateEdge } from '../hooks/useEdgeRankings';
import { EdgeRankingTable } from '../components/EdgeRankingTable';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';

/**
 * Edge Discovery page — lists edge rankings with controls for
 * generating snapshots and toggling insufficient edges.
 */
export default function EdgeDiscoveryPage() {
  const [showInsufficient, setShowInsufficient] = useState(false);
  const rankings = useEdgeRankings(showInsufficient);
  const generate = useGenerateEdge();

  const handleToggle = () => setShowInsufficient((prev) => !prev);

  const handleGenerate = () => {
    generate.mutate();
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Edge Discovery</h1>
          <p className="mt-1 text-sm text-gray-500">
            Identify statistically significant trading edges across dimension
            groups
          </p>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generate.isPending}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {generate.isPending ? 'Generating...' : 'Generate Snapshot'}
        </button>
      </div>

      {generate.isError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Failed to generate snapshot: {generate.error?.message || 'Unknown error'}
        </div>
      )}

      {generate.data && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Snapshot generated: {generate.data.snapshot_id}
        </div>
      )}

      <ErrorBoundary>
        <EdgeRankingTable
          data={rankings.data}
          isLoading={rankings.isLoading}
          isError={rankings.isError}
          error={rankings.error}
          onRetry={rankings.refetch}
          showInsufficient={showInsufficient}
          onToggleInsufficient={handleToggle}
        />
      </ErrorBoundary>
    </div>
  );
}
