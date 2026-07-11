import { api } from '../../../shared/lib/api';

const BASE_PATH = '/analytics/edges';

/**
 * API bridge for all edge discovery endpoints.
 * @see EdgeRankingResponse, EdgeDetailResponse, TagImpact, MistakeImpact, SnapshotInfo
 */
export const edgeDiscoveryApi = {
  /** Generate a new edge snapshot (POST). */
  generate: () =>
    api.post(BASE_PATH, {}),

  /** Fetch edge rankings, optionally including insufficient edges. */
  getRankings: (showInsufficient) =>
    api.get(BASE_PATH, { params: { show_insufficient: showInsufficient } }),

  /** Fetch detail (edge + trades) for a single group. */
  getEdge: (groupId) =>
    api.get(`${BASE_PATH}/${groupId}`),

  /** Fetch tag impact breakdown. */
  getTags: () =>
    api.get(`${BASE_PATH}/tags`),

  /** Fetch mistake impact breakdown. */
  getMistakes: () =>
    api.get(`${BASE_PATH}/mistakes`),

  /** List all available snapshots. */
  listSnapshots: () =>
    api.get(`${BASE_PATH}/snapshots`),

  /** Fetch a specific snapshot's rankings. */
  getSnapshot: (snapshotId) =>
    api.get(`${BASE_PATH}/snapshots/${snapshotId}`),
};
