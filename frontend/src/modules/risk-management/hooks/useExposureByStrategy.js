import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from '../../analytics/hooks/useDashboardFilters';
import { riskAnalyticsApi } from '../services/riskAnalyticsApi';

/**
 * Fetch exposure grouped by strategy.
 * Refetches automatically when filters change via the query key.
 */
export function useExposureByStrategy() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: ['exposure', 'by-strategy', filters],
    queryFn: () => riskAnalyticsApi.getExposureByStrategy(filters),
  });
}
