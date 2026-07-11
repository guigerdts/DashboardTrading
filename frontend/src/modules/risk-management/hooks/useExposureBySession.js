import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from '../../analytics/hooks/useDashboardFilters';
import { riskAnalyticsApi } from '../services/riskAnalyticsApi';

/**
 * Fetch exposure grouped by market session.
 * Refetches automatically when filters change via the query key.
 */
export function useExposureBySession() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: ['exposure', 'by-session', filters],
    queryFn: () => riskAnalyticsApi.getExposureBySession(filters),
  });
}
