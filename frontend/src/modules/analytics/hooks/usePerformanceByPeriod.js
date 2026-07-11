import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/analyticsApi';
import { QUERY_KEYS } from '../utils/constants';

/**
 * Fetch performance metrics grouped by calendar period.
 * Accepts filters and period from the parent.
 *
 * @param {object} filters - Filter params (accountId, dateFrom, dateTo)
 * @param {string} [period='month'] - Grouping period: 'month', 'quarter', 'year'
 */
export function usePerformanceByPeriod(filters, period = 'month') {
  return useQuery({
    queryKey: QUERY_KEYS.performanceByPeriod(filters, period),
    queryFn: () => analyticsApi.getPerformanceByPeriod(filters, period),
  });
}
