import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from '../../analytics/hooks/useDashboardFilters';
import { riskAnalyticsApi } from '../services/riskAnalyticsApi';

/**
 * Fetch exposure grouped by asset.
 * Refetches automatically when filters change via the query key.
 */
export function useExposureByAsset() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: ['exposure', 'by-asset', filters],
    queryFn: () => riskAnalyticsApi.getExposureByAsset(filters),
  });
}
