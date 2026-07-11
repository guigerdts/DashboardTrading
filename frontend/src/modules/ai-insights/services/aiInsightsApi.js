import { api } from '../../../shared/lib/api';

const BASE = '/api/ai-insights';

/**
 * API bridge for all AI Insights endpoints.
 */
export const aiInsightsApi = {
  /** Fetch AI insights summary with optional filters. */
  getSummary: (filters = {}) =>
    api.get(`${BASE}/summary`, { params: filters }),

  /** Fetch full detail for a single insight. */
  getDetail: (insightId) =>
    api.get(`${BASE}/detail/${insightId}`),

  /** Trigger a refresh of AI insights analysis. */
  refresh: (filters = {}) =>
    api.post(`${BASE}/refresh`, filters),
};
