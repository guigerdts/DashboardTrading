import { useDashboardFilters } from '../modules/analytics/hooks/useDashboardFilters';
import { ErrorBoundary } from '../shared/components/ErrorBoundary';
import { RiskDashboard } from '../modules/risk-management/components/RiskDashboard';

function RiskManagement() {
  const { filters } = useDashboardFilters();

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Risk Management</h1>

      <ErrorBoundary>
        <RiskDashboard filters={filters} />
      </ErrorBoundary>
    </div>
  );
}

export default RiskManagement;
