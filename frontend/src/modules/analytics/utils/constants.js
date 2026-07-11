/**
 * Shared constants for the analytics dashboard module.
 */

/** Query key factories for React Query — call with current filters */
export const QUERY_KEYS = {
  summary: (filters) => ['analytics', 'summary', filters],
  equity: (filters) => ['analytics', 'equity', filters],
  assetBreakdown: (filters) => ['analytics', 'breakdown/asset', filters],
  directionBreakdown: (filters) => ['analytics', 'breakdown/direction', filters],
  breakdownStrategies: (filters) => ['analytics', 'breakdown/strategies', filters],
  breakdownSetups: (filters) => ['analytics', 'breakdown/setups', filters],
  breakdownTags: (filters) => ['analytics', 'breakdown/tags', filters],
  breakdownMistakes: (filters) => ['analytics', 'breakdown/mistakes', filters],
  rDistribution: (filters) => ['analytics', 'distribution/r', filters],
  heatmap: (filters) => ['analytics', 'heatmap', filters],
};

/** Default empty filter state */
export const DEFAULT_FILTERS = {
  accountId: null,
  dateFrom: null,
  dateTo: null,
};

/** Chart color palette */
export const CHART_COLORS = {
  primary: '#10b981',
  primaryLight: '#6ee7b7',
  gradientStart: '#10b981',
  gradientEnd: '#34d399',
  positive: '#10b981',
  negative: '#ef4444',
  neutral: '#6b7280',
  grid: '#f0f0f0',
};
