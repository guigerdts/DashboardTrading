import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from '../../analytics/hooks/useDashboardFilters';
import { riskAnalyticsApi } from '../services/riskAnalyticsApi';

/**
 * Fetch cross-asset correlation data.
 * Refetches automatically when filters change via the query key.
 */
export function useCorrelation(minTrades) {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: ['exposure', 'correlation', filters],
    queryFn: () => riskAnalyticsApi.getCorrelation(filters, minTrades),
  });
}
