import { useInsights, useRefreshInsights } from '../hooks/useInsights';
import { AIInsightsDashboard } from '../components/AIInsightsDashboard';

/**
 * AI Insights page — lists insights grouped by severity with a refresh control.
 * Integrates with dashboard filters when available.
 */
export default function AIInsightsPage() {
  const insights = useInsights();
  const refresh = useRefreshInsights();

  const handleRefresh = () => {
    refresh.mutate();
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Insights</h1>
          <p className="mt-1 text-sm text-gray-500">
            Automated analysis of trading patterns, risks, and opportunities
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={refresh.isPending}
          className="inline-flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {refresh.isPending ? (
            <>
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Refreshing...
            </>
          ) : (
            'Refresh'
          )}
        </button>
      </div>

      {refresh.isError && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Failed to refresh insights: {refresh.error?.message || 'Unknown error'}
        </div>
      )}

      {refresh.data && (
        <div className="mb-4 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Insights refresh triggered
        </div>
      )}

      <AIInsightsDashboard
        data={insights.data}
        isLoading={insights.isLoading}
        isError={insights.isError}
        error={insights.error}
        onRetry={insights.refetch}
      />
    </div>
  );
}
