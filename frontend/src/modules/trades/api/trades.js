import { api } from '../../../shared/lib/api';

/**
 * Convert camelCase filter keys to snake_case query params.
 * Omits null/empty values to keep the URL clean.
 */
function buildParams(filters = {}) {
  const params = {};
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.direction) params.direction = filters.direction;
  if (filters.accountId) params.account_id = filters.accountId;
  if (filters.assetId) params.asset_id = filters.assetId;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.sortBy) params.sort_by = filters.sortBy;
  if (filters.sortDir) params.sort_dir = filters.sortDir;
  if (filters.page) params.page = filters.page;
  if (filters.pageSize) params.page_size = filters.pageSize;
  return params;
}

/**
 * Build params for the summary endpoint — excludes pagination/sort params
 * since they don't apply to aggregation.
 */
function buildSummaryParams(filters = {}) {
  const params = {};
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.direction) params.direction = filters.direction;
  if (filters.accountId) params.account_id = filters.accountId;
  if (filters.assetId) params.asset_id = filters.assetId;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  return params;
}

/** API bridge for all trading journal endpoints */
export const tradesApi = {
  /**
   * Fetch paginated trades list.
   * @param {object} filters
   * @param {{ signal?: AbortSignal }} [options]
   * @returns {Promise<{ items: Array, total: number, page: number, pages: number }>}
   */
  list: (filters, { signal } = {}) =>
    api.get('/trades', { params: buildParams(filters), signal }),

  /**
   * Fetch aggregated trade summary.
   * @param {object} filters
   * @param {{ signal?: AbortSignal }} [options]
   * @returns {Promise<{ total_trades: number, total_pnl: number, win_count: number, loss_count: number, win_rate: number, avg_win: number, avg_loss: number, profit_factor: number | null }>}
   */
  summary: (filters, { signal } = {}) =>
    api.get('/trades/summary', { params: buildSummaryParams(filters), signal }),
};
