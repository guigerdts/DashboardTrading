import { useParams, useNavigate } from 'react-router-dom';
import { useEdgeDetail } from '../hooks/useEdgeDetail';
import { EdgeScoreCard } from '../components/EdgeScoreCard';
import { EdgeDetailDrilldown } from '../components/EdgeDetailDrilldown';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';

/**
 * Detail page for a single edge group — shows metrics card + trade list.
 */
export default function EdgeDetailPage() {
  const { group_id } = useParams();
  const navigate = useNavigate();
  const detail = useEdgeDetail(group_id);

  const edge = detail.data?.edge;

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => navigate('/analytics/edges')}
          className="mb-4 inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
        >
          &larr; Back to rankings
        </button>

        <h1 className="text-2xl font-bold text-gray-900">Edge Detail</h1>
        {edge && (
          <p className="mt-1 text-sm text-gray-500">
            {Object.entries(edge.dimensions)
              .filter(([, v]) => v != null)
              .map(([, v]) => v)
              .join(' · ')}
          </p>
        )}
      </div>

      <ErrorBoundary>
        <div className="mb-6">
          <EdgeScoreCard
            data={detail.data}
            isLoading={detail.isLoading}
            isError={detail.isError}
            error={detail.error}
            onRetry={detail.refetch}
          />
        </div>
      </ErrorBoundary>

      <ErrorBoundary>
        <EdgeDetailDrilldown
          data={detail.data}
          isLoading={detail.isLoading}
          isError={detail.isError}
          error={detail.error}
          onRetry={detail.refetch}
        />
      </ErrorBoundary>
    </div>
  );
}
