import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';
import { useRiskMetrics } from '../hooks/useRiskMetrics';
import { useExposureByAsset } from '../hooks/useExposureByAsset';
import { useExposureBySession } from '../hooks/useExposureBySession';
import { useExposureByStrategy } from '../hooks/useExposureByStrategy';
import { useCorrelation } from '../hooks/useCorrelation';
import { RiskMetricsCards } from './RiskMetricsCards';
import { ExposureTable } from './ExposureTable';
import { CorrelationMatrix } from './CorrelationMatrix';

/**
 * Risk dashboard composite — fetches all 5 hooks, renders child components.
 * Each widget is wrapped in an ErrorBoundary so a crash in one doesn't
 * take down the entire page.
 *
 * @param {{ filters }} props
 */
export function RiskDashboard({ filters }) {
  const riskMetrics = useRiskMetrics();
  const exposureByAsset = useExposureByAsset();
  const exposureBySession = useExposureBySession();
  const exposureByStrategy = useExposureByStrategy();
  const correlation = useCorrelation();

  return (
    <div className="space-y-6">
      {/* Risk metrics cards grid */}
      <ErrorBoundary>
        <RiskMetricsCards
          data={riskMetrics.data}
          isLoading={riskMetrics.isLoading}
          isError={riskMetrics.isError}
          error={riskMetrics.error}
          onRetry={riskMetrics.refetch}
        />
      </ErrorBoundary>

      {/* Exposure table — asset, session, strategy tabs */}
      <ErrorBoundary>
        <ExposureTable
          byAssetData={exposureByAsset.data}
          bySessionData={exposureBySession.data}
          byStrategyData={exposureByStrategy.data}
          isLoading={
            exposureByAsset.isLoading ||
            exposureBySession.isLoading ||
            exposureByStrategy.isLoading
          }
          isError={
            exposureByAsset.isError ||
            exposureBySession.isError ||
            exposureByStrategy.isError
          }
          error={exposureByAsset.error || exposureBySession.error || exposureByStrategy.error}
          onRetry={() => {
            exposureByAsset.refetch();
            exposureBySession.refetch();
            exposureByStrategy.refetch();
          }}
        />
      </ErrorBoundary>

      {/* Correlation matrix */}
      <ErrorBoundary>
        <CorrelationMatrix
          data={correlation.data}
          isLoading={correlation.isLoading}
          isError={correlation.isError}
          error={correlation.error}
          onRetry={correlation.refetch}
        />
      </ErrorBoundary>
    </div>
  );
}
