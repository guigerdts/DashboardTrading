import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { aiInsightsApi } from '../services/aiInsightsApi';

/**
 * Fetch AI insights summary.
 * Refetches when filters change via the query key.
 *
 * @param {object} [filters={}] — filter params (accountId, dateFrom, dateTo, etc.)
 * @returns {{ data, isLoading, isError, error, refetch }}
 */
export function useInsights(filters = {}) {
  return useQuery({
    queryKey: ['ai-insights', 'summary', filters],
    queryFn: () => aiInsightsApi.getSummary(filters),
  });
}

/**
 * Fetch full detail for a single insight.
 * Only enabled when insightId is truthy.
 *
 * @param {string|number|null} insightId
 * @returns {{ data, isLoading, isError, error, refetch }}
 */
export function useInsightDetail(insightId) {
  return useQuery({
    queryKey: ['ai-insights', 'detail', insightId],
    queryFn: () => aiInsightsApi.getDetail(insightId),
    enabled: !!insightId,
  });
}

/**
 * Mutation to trigger a fresh AI analysis.
 * Invalidates the summary query on success.
 *
 * @returns {{ mutate, isPending, isError, error, data }}
 */
export function useRefreshInsights() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (filters) => aiInsightsApi.refresh(filters),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-insights', 'summary'] });
    },
  });
}
