/**
 * Edge score for a single dimension group.
 * @typedef {Object} EdgeScore
 * @property {string} group_id
 * @property {Record<string, string|null>} dimensions
 * @property {number[]} trade_ids
 * @property {number} trade_count
 * @property {number} expectancy
 * @property {number} net_pnl
 * @property {number|null} profit_factor
 * @property {[number, number]} confidence_interval
 * @property {number} p_value
 * @property {number} fdr_adjusted_p_value
 * @property {number} stability_score
 * @property {number} edge_score
 * @property {'high'|'medium'|'low'|'insufficient'} confidence_level
 * @property {string[]} failure_reasons
 */

/**
 * Full edge ranking response from /api/analytics/edges.
 * @typedef {Object} EdgeRankingResponse
 * @property {string} snapshot_id
 * @property {string} generated_at
 * @property {EdgeGenerateParams} parameters
 * @property {number} trade_count
 * @property {EdgeScore[]} rankings
 */

/**
 * Edge detail response with trade list.
 * @typedef {Object} EdgeDetailResponse
 * @property {EdgeScore} edge
 * @property {TradeSummary[]} trades
 */

/**
 * Tag impact breakdown.
 * @typedef {Object} TagImpact
 * @property {string} tag
 * @property {number} trade_count
 * @property {number} avg_pnl
 * @property {number} total_pnl
 */

/**
 * Mistake impact breakdown.
 * @typedef {Object} MistakeImpact
 * @property {string} mistake
 * @property {number} trade_count
 * @property {number} avg_pnl
 * @property {number} total_pnl
 * @property {number} frequency
 */

/**
 * Snapshot metadata.
 * @typedef {Object} SnapshotInfo
 * @property {string} snapshot_id
 * @property {string} created_at
 * @property {number} trade_count
 * @property {number} group_count
 */

/**
 * Parameters used to generate the edge snapshot.
 * @typedef {Object} EdgeGenerateParams
 * @property {number} min_observations
 * @property {number} bootstrap_resamples
 * @property {number} fdr_alpha
 * @property {number} stability_threshold
 * @property {number|null} seed
 */

/**
 * Summary of a single trade for edge detail.
 * @typedef {Object} TradeSummary
 * @property {number} id
 * @property {string|null} strategy
 * @property {string|null} setup
 * @property {string|null} asset
 * @property {string|null} direction
 * @property {number} pnl
 * @property {string[]} tags
 * @property {string[]} mistakes
 */

export {};
