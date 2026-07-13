import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { useExperiments, useCreateExperiment } from '../hooks/useStrategyLab';

const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-700 border-gray-200',
  running: 'bg-blue-100 text-blue-700 border-blue-200',
  completed: 'bg-green-100 text-green-700 border-green-200',
  aborted: 'bg-red-100 text-red-700 border-red-200',
};

const DEFAULT_STATUS = STATUS_STYLES.draft;

/**
 * List of strategy-lab experiments with create and navigation controls.
 *
 * @param {{ onNavigate?: (id) => void }} props
 */
export function ExperimentList() {
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useExperiments();
  const createExperiment = useCreateExperiment();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', hypothesis: '' });

  const experiments = data?.experiments;

  const handleCreate = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    createExperiment.mutate(formData, {
      onSuccess: () => {
        setShowForm(false);
        setFormData({ name: '', hypothesis: '' });
      },
    });
  };

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load experiments'}
        onRetry={refetch}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <Skeleton variant="text" width="180px" />
          <Skeleton variant="rect" height={36} width={140} />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="mb-3 flex items-center gap-4 border-b border-gray-100 pb-3 last:border-0">
            <Skeleton variant="rect" height={20} width="40%" />
            <Skeleton variant="rect" height={20} width={80} />
            <Skeleton variant="rect" height={20} width={100} />
          </div>
        ))}
      </div>
    );
  }

  if (!experiments || experiments.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Experiments</h2>
          <button
            onClick={() => setShowForm(true)}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New Experiment
          </button>
        </div>
        {showForm && (
          <form onSubmit={handleCreate} className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="exp-name">
                Name
              </label>
              <input
                id="exp-name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="e.g. Trend Following v2"
                required
              />
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="exp-hypothesis">
                Hypothesis
              </label>
              <textarea
                id="exp-hypothesis"
                value={formData.hypothesis}
                onChange={(e) => setFormData((prev) => ({ ...prev, hypothesis: e.target.value }))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                rows={2}
                placeholder="What are you testing?"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createExperiment.isPending || !formData.name.trim()}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {createExperiment.isPending ? 'Creating...' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
            {createExperiment.isError && (
              <p className="mt-2 text-sm text-red-600">
                Failed to create experiment: {createExperiment.error?.message || 'Unknown error'}
              </p>
            )}
          </form>
        )}
        <div className="flex h-[120px] items-center justify-center">
          <p className="text-gray-400">No experiments yet</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Experiments ({experiments.length})
        </h2>
        <button
          onClick={() => setShowForm(true)}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Experiment
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="exp-name">
              Name
            </label>
            <input
              id="exp-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              placeholder="e.g. Trend Following v2"
              required
            />
          </div>
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700" htmlFor="exp-hypothesis">
              Hypothesis
            </label>
            <textarea
              id="exp-hypothesis"
              value={formData.hypothesis}
              onChange={(e) => setFormData((prev) => ({ ...prev, hypothesis: e.target.value }))}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              rows={2}
              placeholder="What are you testing?"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createExperiment.isPending || !formData.name.trim()}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createExperiment.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded bg-gray-100 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200"
            >
              Cancel
            </button>
          </div>
          {createExperiment.isError && (
            <p className="mt-2 text-sm text-red-600">
              Failed to create experiment: {createExperiment.error?.message || 'Unknown error'}
            </p>
          )}
        </form>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Name</th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Hypothesis</th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Status</th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Created</th>
            </tr>
          </thead>
          <tbody>
            {experiments.map((exp) => {
              const statusStyle = STATUS_STYLES[exp.status] || DEFAULT_STATUS;
              return (
                <tr
                  key={exp.id}
                  onClick={() => navigate(`/lab/experiments/${exp.id}`)}
                  className="cursor-pointer border-b border-gray-100 last:border-0 hover:bg-gray-50"
                >
                  <td className="py-3 pr-2 font-medium text-gray-900">{exp.name}</td>
                  <td className="py-3 pr-2 text-gray-600 max-w-[300px] truncate">
                    {exp.hypothesis || '—'}
                  </td>
                  <td className="py-3 pr-2">
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${statusStyle}`}
                    >
                      {exp.status ? exp.status.charAt(0).toUpperCase() + exp.status.slice(1) : 'Unknown'}
                    </span>
                  </td>
                  <td className="py-3 text-gray-500 text-xs">
                    {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
