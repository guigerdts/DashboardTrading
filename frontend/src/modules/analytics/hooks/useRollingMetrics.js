import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch rolling windowed metrics.
 * Accepts filters from the parent (DashboardPage).
 *
 * @param {object} filters - Filter params (accountId, dateFrom, dateTo, windowSize)
 */
export function useRollingMetrics(filters) {
  return useQuery({
    queryKey: QUERY_KEYS.rolling(filters),
    queryFn: () => analyticsApi.getRolling(filters),
  });
}
