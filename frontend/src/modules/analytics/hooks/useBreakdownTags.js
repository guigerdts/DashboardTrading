import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch per-tag breakdown (P&L, Win Rate, Trade Count, Profit Factor).
 * Refetches automatically when filters change via the query key.
 */
export function useBreakdownTags() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.breakdownTags(filters),
    queryFn: () => analyticsApi.getBreakdownTags(filters),
  });
}
