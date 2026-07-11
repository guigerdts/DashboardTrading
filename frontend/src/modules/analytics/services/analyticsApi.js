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
};

// @gap: no UI consumer
export async function getPerformance(filters) {
  throw new Error('getPerformance is not implemented — no UI consumer yet');
}

// @gap: no UI consumer
export async function getMarketBreakdown(filters) {
  throw new Error('getMarketBreakdown is not implemented — no UI consumer yet');
}
