import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from '../../analytics/hooks/useDashboardFilters';
import { riskAnalyticsApi } from '../services/riskAnalyticsApi';

/**
 * Fetch risk metrics (streaks, holding time, Kelly, RoR, expectancy-adjusted).
 * Refetches automatically when filters or capital change via the query key.
 */
export function useRiskMetrics(capital) {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: ['risk-metrics', filters, capital],
    queryFn: () => riskAnalyticsApi.getRiskMetrics(filters, capital),
  });
}
