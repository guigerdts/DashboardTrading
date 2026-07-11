import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch period comparison data (two date ranges).
 * Accepts filters from the parent, which must include period_a_from/period_a_to
 * and period_b_from/period_b_to.
 *
 * @param {object} filters - Filter params including date ranges for both periods
 */
export function usePerformanceComparison(filters) {
  return useQuery({
    queryKey: QUERY_KEYS.compare(filters),
    queryFn: () => analyticsApi.comparePeriods(filters),
  });
}
