import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch per-mistake breakdown (P&L, Win Rate, Trade Count, Profit Factor).
 * Refetches automatically when filters change via the query key.
 */
export function useBreakdownMistakes() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.breakdownMistakes(filters),
    queryFn: () => analyticsApi.getBreakdownMistakes(filters),
  });
}
