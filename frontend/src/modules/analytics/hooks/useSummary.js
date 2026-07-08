import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch summary performance metrics (Net P&L, Win Rate, Profit Factor, Expectancy, Max Drawdown).
 * Refetches automatically when filters change via the query key.
 */
export function useSummary() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.summary(filters),
    queryFn: () => analyticsApi.getSummary(filters),
  });
}
