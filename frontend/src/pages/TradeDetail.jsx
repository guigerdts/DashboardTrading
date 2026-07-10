import { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ErrorBoundary } from '../shared/components/ErrorBoundary';
import { useTradeDetail } from '../modules/trade-review/hooks/useTradeDetail';
import { useTradeReview } from '../modules/trade-review/hooks/useTradeReview';
import { TradeHeader } from '../modules/trade-review/components/TradeHeader';
import { ExecutionDetails } from '../modules/trade-review/components/ExecutionDetails';
import { RiskDetails } from '../modules/trade-review/components/RiskDetails';
import { ReviewEditor } from '../modules/trade-review/components/ReviewEditor';
import { ContextSection } from '../modules/trade-review/components/ContextSection';

export default function TradeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const tradeId = parseInt(id, 10);
  const { data, isLoading, isError, error, isNotFound, refetch } = useTradeDetail(tradeId);
  const { save, isSaving, isSuccess, isError: isReviewError, error: reviewError, reset } = useTradeReview(tradeId);

  useEffect(() => {
    if (isSuccess) {
      refetch();
    }
  }, [isSuccess, refetch]);

  if (isNotFound) {
    return (
      <div className="p-6">
        <div className="flex flex-col items-center justify-center rounded-lg border border-gray-200 bg-white p-12 text-center shadow-sm">
          <p className="mb-2 text-lg font-medium text-gray-900">Trade not found</p>
          <p className="mb-6 text-sm text-gray-500">The trade you are looking for does not exist or has been removed.</p>
          <Link to="/trading-journal" className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
            Back to Journal
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <button
          onClick={() => navigate('/trading-journal')}
          className="mb-4 text-sm text-blue-600 hover:text-blue-700"
        >
          &larr; Back to Journal
        </button>
      </div>

      <ErrorBoundary>
        <div className="mb-6">
          <TradeHeader data={data} isLoading={isLoading} isError={isError} error={error} onRetry={refetch} />
        </div>
      </ErrorBoundary>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <ErrorBoundary>
          <ExecutionDetails data={data} isLoading={isLoading} />
        </ErrorBoundary>
        <ErrorBoundary>
          <RiskDetails data={data} isLoading={isLoading} />
        </ErrorBoundary>
      </div>

      <ErrorBoundary>
        <div className="mb-6">
          <ContextSection data={data} isLoading={isLoading} />
        </div>
      </ErrorBoundary>

      <ErrorBoundary>
        <div className="mb-6">
          <ReviewEditor
            review={data?.review}
            isLoading={isLoading}
            onSave={save}
            isSaving={isSaving}
            isError={isReviewError}
            error={reviewError}
            reset={reset}
          />
        </div>
      </ErrorBoundary>
    </div>
  );
}
