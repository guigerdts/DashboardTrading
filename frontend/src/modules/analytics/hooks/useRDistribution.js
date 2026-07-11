import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch R-multiple distribution data for the histogram chart.
 * Refetches automatically when filters change via the query key.
 */
export function useRDistribution() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.rDistribution(filters),
    queryFn: () => analyticsApi.getRDistribution(filters),
  });
}
