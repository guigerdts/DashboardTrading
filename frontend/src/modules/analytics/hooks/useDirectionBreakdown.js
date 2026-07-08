import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch Long vs Short direction breakdown.
 * Refetches automatically when filters change via the query key.
 */
export function useDirectionBreakdown() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.directionBreakdown(filters),
    queryFn: () => analyticsApi.getDirectionBreakdown(filters),
  });
}
