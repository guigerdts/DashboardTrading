import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch equity curve data for the chart.
 * Refetches automatically when filters change via the query key.
 */
export function useEquity() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.equity(filters),
    queryFn: () => analyticsApi.getEquity(filters),
  });
}
