import { useState } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { useExperiment, useCreateRun, useStrategyVersions } from '../hooks/useStrategyLab';

const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-700 border-gray-200',
  running: 'bg-blue-100 text-blue-700 border-blue-200',
  completed: 'bg-green-100 text-green-700 border-green-200',
  aborted: 'bg-red-100 text-red-700 border-red-200',
};

const RUN_STATUS_STYLES = {
  pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  running: 'bg-blue-100 text-blue-700 border-blue-200',
  completed: 'bg-green-100 text-green-700 border-green-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
};

const DEFAULT_STATUS = STATUS_STYLES.draft;
const DEFAULT_RUN_STATUS = RUN_STATUS_STYLES.pending;

/**
 * Detail view for a single experiment — shows metadata, runs list, and "New Run" form.
 *
 * @param {{ experimentId: string|number }} props
 */
export function ExperimentDetail({ experimentId }) {
  const { data, isLoading, isError, error, refetch } = useExperiment(experimentId);
  const [showRunForm, setShowRunForm] = useState(false);
  const createRun = useCreateRun();
  const [selectedVersion, setSelectedVersion] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Fetch strategy versions for the run form
  const versionsQuery = useStrategyVersions(experimentId);

  const experiment = data?.experiment;
  const runs = data?.runs || [];
  const versions = versionsQuery.data?.versions || [];

  const handleCreateRun = (e) => {
    e.preventDefault();
    if (!selectedVersion) return;
    createRun.mutate(
      {
        experiment_id: experimentId,
        strategy_version_id: selectedVersion,
        ...(dateFrom && { date_from: dateFrom }),
        ...(dateTo && { date_to: dateTo }),
      },
      {
        onSuccess: () => {
          setShowRunForm(false);
          setSelectedVersion('');
          setDateFrom('');
          setDateTo('');
        },
      },
    );
  };

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load experiment'}
        onRetry={refetch}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="200px" className="mb-2" />
        <Skeleton variant="text" width="100%" className="mb-1" />
        <Skeleton variant="text" width="80%" className="mb-4" />
        <Skeleton variant="rect" height={24} width={80} className="mb-4" />
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="mb-2 flex gap-4">
            <Skeleton variant="rect" height={20} width="30%" />
            <Skeleton variant="rect" height={20} width="20%" />
            <Skeleton variant="rect" height={20} width="20%" />
          </div>
        ))}
      </div>
    );
  }

  if (!experiment) {
    return (
      <div className="flex h-[200px] items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
        <p className="text-gray-400">Experiment not found</p>
      </div>
    );
  }

  const expStatusStyle = STATUS_STYLES[experiment.status] || DEFAULT_STATUS;

  return (
    <div className="space-y-6">
      {/* Experiment Metadata */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-gray-900">{experiment.name}</h2>
          <span
            className={`mt-2 inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${expStatusStyle}`}
          >
            {experiment.status
              ? experiment.status.charAt(0).toUpperCase() + experiment.status.slice(1)
              : 'Unknown'}
          </span>
        </div>

        {experiment.hypothesis && (
          <div className="mb-4 rounded-md bg-gray-50 p-3">
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-gray-500">
              Hypothesis
            </h3>
            <p className="text-sm text-gray-700">{experiment.hypothesis}</p>
          </div>
        )}

        {experiment.created_at && (
          <p className="text-xs text-gray-400">
            Created: {new Date(experiment.created_at).toLocaleString()}
          </p>
        )}
      </div>

      {/* Runs Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-500">Runs ({runs.length})</h3>
          <button
            onClick={() => setShowRunForm(true)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New Run
          </button>
        </div>

        {/* New Run Form */}
        {showRunForm && (
          <form onSubmit={handleCreateRun} className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="run-version">
                Strategy Version
              </label>
              <select
                id="run-version"
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                required
              >
                <option value="">Select a version...</option>
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.label || `Version #${v.id}`}
                  </option>
                ))}
              </select>
              {versionsQuery.isLoading && (
                <p className="mt-1 text-xs text-gray-400">Loading versions...</p>
              )}
            </div>

            <div className="mb-3 flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="run-date-from">
                  Date From
                </label>
                <input
                  id="run-date-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="run-date-to">
                  Date To
                </label>
                <input
                  id="run-date-to"
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createRun.isPending || !selectedVersion}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {createRun.isPending ? 'Starting...' : 'Start Run'}
              </button>
              <button
                type="button"
                onClick={() => setShowRunForm(false)}
                className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
            {createRun.isError && (
              <p className="mt-2 text-sm text-red-600">
                Failed to create run: {createRun.error?.message || 'Unknown error'}
              </p>
            )}
          </form>
        )}

        {/* Runs List */}
        {runs.length === 0 ? (
          <div className="flex h-[100px] items-center justify-center">
            <p className="text-gray-400">No runs yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Status
                  </th>
                  <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Created
                  </th>
                  <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Engine
                  </th>
                  <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                    Metrics
                  </th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => {
                  const runStatusStyle = RUN_STATUS_STYLES[run.status] || DEFAULT_RUN_STATUS;
                  return (
                    <tr key={run.id} className="border-b border-gray-100 last:border-0">
                      <td className="py-2 pr-2">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${runStatusStyle}`}
                        >
                          {run.status
                            ? run.status.charAt(0).toUpperCase() + run.status.slice(1)
                            : 'Unknown'}
                        </span>
                      </td>
                      <td className="py-2 pr-2 text-gray-600 text-xs">
                        {run.created_at
                          ? new Date(run.created_at).toLocaleString()
                          : '—'}
                      </td>
                      <td className="py-2 pr-2 text-gray-600 text-xs">
                        {run.engine_version || '—'}
                      </td>
                      <td className="py-2 text-gray-600 text-xs">
                        {run.metrics_count ?? '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
