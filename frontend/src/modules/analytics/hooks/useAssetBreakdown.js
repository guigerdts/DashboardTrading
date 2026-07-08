import { useQuery } from '@tanstack/react-query';
import { useDashboardFilters } from './useDashboardFilters';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch per-asset performance breakdown (Symbol, Net P&L, Win Rate, Trade Count, Profit Factor).
 * Refetches automatically when filters change via the query key.
 */
export function useAssetBreakdown() {
  const { filters } = useDashboardFilters();

  return useQuery({
    queryKey: QUERY_KEYS.assetBreakdown(filters),
    queryFn: () => analyticsApi.getAssetBreakdown(filters),
  });
}
