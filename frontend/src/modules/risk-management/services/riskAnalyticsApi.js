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

/** API bridge for risk analytics endpoints */
export const riskAnalyticsApi = {
  getRiskMetrics: (filters, capital) =>
    api.get('/analytics/risk-metrics', {
      params: { ...buildParams(filters), ...(capital !== undefined ? { capital } : {}) },
    }),

  getExposureByAsset: (filters) =>
    api.get('/analytics/exposure/by-asset', { params: buildParams(filters) }),

  getExposureBySession: (filters) =>
    api.get('/analytics/exposure/by-session', { params: buildParams(filters) }),

  getExposureByStrategy: (filters) =>
    api.get('/analytics/exposure/by-strategy', { params: buildParams(filters) }),

  getCorrelation: (filters, minTrades = 30) =>
    api.get('/analytics/exposure/correlation', {
      params: { ...buildParams(filters), min_trades: minTrades },
    }),
};
