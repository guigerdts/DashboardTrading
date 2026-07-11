import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch heatmap data (P&L by day-of-week × hour).
 * Refetches automatically when filters change via the query key.
 */
export function useHeatmap() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.heatmap(filters),
    queryFn: () => analyticsApi.getHeatmap(filters),
  });
}
