import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch per-strategy breakdown (P&L, Win Rate, Trade Count, Profit Factor).
 * Refetches automatically when filters change via the query key.
 */
export function useBreakdownStrategies() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.breakdownStrategies(filters),
    queryFn: () => analyticsApi.getBreakdownStrategies(filters),
  });
}
