import { api } from '../../../shared/lib/api';

const BASE = '/api/strategy-lab';

export const strategyLabApi = {
  // Strategy Versions
  getStrategyVersions: (strategyId) => api.get(`${BASE}/strategy-versions`, { params: { strategy_id: strategyId } }),
  createStrategyVersion: (data) => api.post(`${BASE}/strategy-versions`, data),
  getStrategyVersion: (id) => api.get(`${BASE}/strategy-versions/${id}`),

  // Experiments
  getExperiments: () => api.get(`${BASE}/experiments`),
  createExperiment: (data) => api.post(`${BASE}/experiments`, data),
  getExperiment: (id) => api.get(`${BASE}/experiments/${id}`),

  // Runs
  getRuns: () => api.get(`${BASE}/runs`),
  createRun: (data) => api.post(`${BASE}/runs`, data),
  getRun: (id) => api.get(`${BASE}/runs/${id}`),
  compareRuns: (runId, baselineId) => api.get(`${BASE}/runs/${runId}/compare`, { params: { baseline_id: baselineId } }),
};
