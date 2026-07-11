import { api } from '../../../shared/lib/api';

/**
 * Convert camelCase filter keys to snake_case query params.
 * Omits null/empty values to keep the URL clean.
 */
function buildParams(filters = {}) {
  const params = {};
  if (filters.accountId) params.account_id = filters.accountId;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.windowSize) params.window_size = filters.windowSize;
  if (filters.periodAFrom) params.period_a_from = filters.periodAFrom;
  if (filters.periodATo) params.period_a_to = filters.periodATo;
  if (filters.periodBFrom) params.period_b_from = filters.periodBFrom;
  if (filters.periodBTo) params.period_b_to = filters.periodBTo;
  return params;
}

/** API bridge for all analytics endpoints */
export const analyticsApi = {
  getSummary: (filters) =>
    api.get('/analytics/summary', { params: buildParams(filters) }),

  getEquity: (filters) =>
    api.get('/analytics/equity', { params: buildParams(filters) }),

  getAssetBreakdown: (filters) =>
    api.get('/analytics/breakdown/asset', { params: buildParams(filters) }),

  getDirectionBreakdown: (filters) =>
    api.get('/analytics/breakdown/direction', { params: buildParams(filters) }),

  getBreakdownStrategies: (filters) =>
    api.get('/analytics/breakdown/strategies', { params: buildParams(filters) }),

  getBreakdownSetups: (filters) =>
    api.get('/analytics/breakdown/setups', { params: buildParams(filters) }),

  getBreakdownTags: (filters) =>
    api.get('/analytics/breakdown/tags', { params: buildParams(filters) }),

  getBreakdownMistakes: (filters) =>
    api.get('/analytics/breakdown/mistakes', { params: buildParams(filters) }),

  getRDistribution: (filters) =>
    api.get('/analytics/distribution/r', { params: buildParams(filters) }),

  getHeatmap: (filters) =>
    api.get('/analytics/heatmap', { params: buildParams(filters) }),

  // ── Rolling / Performance / Compare ──────────────────────────────────────

  getRolling: (filters) =>
    api.get('/analytics/rolling', { params: buildParams(filters) }),

  getPerformanceByPeriod: (filters, period) =>
    api.get('/analytics/performance/by-period', {
      params: { ...buildParams(filters), period },
    }),

  comparePeriods: (filters) =>
    api.get('/analytics/performance/compare', {
      params: buildParams(filters),
    }),
};

// @gap: no UI consumer
export async function getMarketBreakdown(filters) {
  throw new Error('getMarketBreakdown is not implemented — no UI consumer yet');
}
