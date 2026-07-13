# Edge Discovery — Exploration Report (v1.4.0)

## 1. What Already Exists

### Existing Breakdown Endpoints (single-dimension)

All under `GET /api/analytics/`:

| Endpoint | Response Model | Groups By | Loads Relations |
|----------|---------------|-----------|-----------------|
| `breakdown/strategies` | `BreakdownResponse` | `trade.strategy_id` | `["strategy"]` |
| `breakdown/setups` | `BreakdownResponse` | `trade.setup_id` | `["setup"]` |
| `breakdown/tags` | `BreakdownResponse` | M:N via `trade_tags` | `["tags"]` |
| `breakdown/mistakes` | `BreakdownResponse` | 1:N via `mistake_entries` | `["mistakes"]` |
| `breakdown/asset` | `AssetBreakdownResponse` | `trade.asset_id` | none |
| `breakdown/direction` | `DirectionBreakdownResponse` | `trade.direction` | none |
| `breakdown/market` | `MarketBreakdownResponse` | `trade.asset.market_id` | none |

All return flat lists sorted by `net_pnl DESC → trade_count DESC → name ASC`.

### Existing Calculator Patterns

All calculators in `backend/app/modules/analytics/calculators/`:

- **Pure functions** taking `list[Trade]`, returning `list[dict]`
- **No class state** — calculators are stateless transformations
- **Pattern**: group by dimension → compute metrics per group → sort → return
- **Core metric function**: `compute_performance()` — single pass computing net_pnl, gross_profit, gross_loss, win_rate, profit_factor, expectancy, avg_win, avg_loss, avg_r_multiple
- **Registry**: `CALCULATORS` dict in `__init__.py` (currently empty — no registration pattern used yet)
- **Reusable concepts**: `compute_exposure_by_session()` shows the pattern for grouping by `market_session_id`

### Existing Schemas

```
BreakdownItem: { id, name, trade_count, win_rate, net_pnl, gross_profit,
                 gross_loss, profit_factor, expectancy, avg_win, avg_loss }
BreakdownResponse: { items: list[BreakdownItem] }
```

`PerformanceMetrics`: { net_pnl, gross_profit, gross_loss, trade_count, win_rate, profit_factor, expectancy, avg_win, avg_loss, avg_r_multiple }

### Existing Frontend

- **`BreakdownTable`** — reusable component rendering `BreakdownItem[]` in a sortable table
- **`SummaryCards`** — 7-card grid with loading/error/empty states
- **Pattern**: each widget uses React Query (`useQuery`) with `QUERY_KEYS` factory pattern
- **`analyticsApi`** — API bridge with `buildParams()` for camelCase→snake_case conversion
- **`DashboardPage`** — orchestrator page that wires filters → queries → components

### Existing Service Pattern

`AnalyticsService`:
1. Parse `AnalyticsFilter` from query params
2. Fetch trades via single `uow.trades.list_closed(**filter_kwargs, load_relations=[...])`
3. Distribute to calculators
4. Map calculator dicts to Pydantic response models
5. Return

### Existing AnalyticsFilter

```python
class AnalyticsFilter(BaseModel):
    account_id: int | None = None
    asset_id: int | None = None
    market_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    window_size: int | None = None
```

### Existing Repository (`list_closed`)

- `load_relations` supports `["strategy", "setup", "tags", "mistakes"]`
- Filters: `account_id`, `asset_id`, `market_id`, `date_from`, `date_to`
- Returns all closed trades with eager loading
- **No `market_session_id` or `direction` filter** — these exist on the model but are not filterable via `list_closed`

---

## 2. Data Model Inventory

### Trade Dimensions Available

| Dimension | Column | Type | Nullable? | Join Path |
|-----------|--------|------|-----------|-----------|
| Strategy | `strategy_id` | FK → strategies | ✅ Yes (SET NULL) | `selectinload(Trade.strategy)` |
| Setup | `setup_id` | FK → setups | ✅ Yes (SET NULL) | `selectinload(Trade.setup)` |
| Asset | `asset_id` | FK → assets | ❌ No (RESTRICT) | `joinedload(Trade.asset)` → `Asset.market_id` |
| Direction | `direction` | TEXT ('long'/'short') | ❌ No | Direct attribute |
| Market Session | `market_session_id` | FK → market_sessions | ✅ Yes (SET NULL) | Join via `market_sessions` table |
| Timeframe | `timeframe_id` | FK → timeframes | ✅ Yes (SET NULL) | Join via `timeframes` table |
| Tag | M:N via `trade_tags` | Junction | N/A | `selectinload(Trade.tags)` |
| Mistake | 1:N via `mistake_entries` | Pivot with notes | N/A | `selectinload(Trade.mistakes)` → `.mistake_id` |
| Account | `account_id` | FK → accounts | ❌ No | `joinedload(Trade.account)` |

### Pivot Table Details

**`trade_tags`** (M:N between Trade ↔ Tag):
- Composite PK: `(trade_id, tag_id)`
- Pure junction — no metadata columns
- A trade contributes its PnL to **every** tag it has

**`mistake_entries`** (1:N between Trade ↔ Mistake):
- PK: `id` (auto-increment)
- Columns: `trade_id`, `mistake_id`, `notes` (nullable)
- A trade with multiple mistakes contributes its PnL to **every** mistake it has

### Key Observations

1. **All dimensions are available** without schema changes
2. **`market_session_id` is not filterable** via `list_closed` — would need either a new param or manual filtering
3. **`direction`, `timeframe_id`** also not filterable in `list_closed` — same issue
4. **`load_relations` can load all 4 context dimensions** (strategy, setup, tags, mistakes) in a single query
5. **No data migration needed** — all FK columns and pivot tables already exist

---

## 3. What's Missing

### Backend — New Module or Extension

| Component | Missing | Priority |
|-----------|---------|----------|
| **Edge Discovery Engine** (calculators) | Nothing cross-tabulates Strategy × Setup × Session × Asset × Direction | P0 |
| **Combination Enumerator** | Must produce only existing combos (not full Cartesian product) | P0 |
| **Bootstrap CI Calculator** | No confidence intervals anywhere in the codebase | P0 |
| **FDR Correction** | No multiple comparison correction anywhere | P0 |
| **Minimum Observations Filter** | Current breakdowns show ALL groups regardless of count | P0 |
| **Stability Test** | No split-sample comparison for edge persistence | P1 |
| **Ranking by Statistical Metric** | Current sorting is by `net_pnl DESC`, not by statistical significance | P0 |
| **Traceability (trade IDs per edge)** | No mechanism to list constituent trades for a combo | P0 |
| **Edge Discovery Schema** | New response models needed | P0 |
| **Edge Discovery Router** | New endpoint(s) needed | P0 |
| **Service Methods** | New `AnalyticsService` methods needed | P0 |

### Frontend — New Components

| Component | Missing | Priority |
|-----------|---------|----------|
| **Edge Ranking Table** | New component (beyond flat BreakdownTable) | P0 |
| **Edge Detail / Drill-Down** | Click edge → see constituent trades | P1 |
| **Significance Indicators** | CI range, p-adjusted value display | P0 |
| **Stability Badge** | Visual indicator for edge stability | P1 |
| **API Bridge & Query Keys** | New entry for edge-discovery endpoints | P0 |

---

## 4. Proposed Statistical Methodology

### Metric Selection for Edge Ranking

| Metric | Use Case | Pros | Cons |
|--------|----------|------|------|
| **Expectancy** | Primary ranking metric | Already computed; intuitive ($/trade) | Sensitive to outliers |
| **Avg R Multiple** | Risk-adjusted complement | Normalized; comparable across strategies | Requires `risk_amount` on every trade |
| **Profit Factor** | Secondary / filter | Easy to interpret | Can be infinite (no losses) |
| **Win Rate** | Secondary | Intuitive | Ignores magnitude |
| **Sharpe-like (PnL / std(PnL))** | Risk-adjusted ranking | Standard in finance | Not currently computed |

**Recommendation**: Use **Expectancy** as the primary ranking metric. Add **Avg R Multiple** as a risk-adjusted view. Apply bootstrap CIs to both.

### Bootstrap CI Approach

- **Method**: Percentile bootstrap (10,000 resamples)
- **CI width**: 95% (2.5%–97.5% percentiles)
- **Procedure**:
  1. For each candidate combination, draw N trades with replacement (N = group size)
  2. Compute expectancy on resampled group
  3. Repeat 10,000× → get distribution
  4. Lower = 2.5th percentile, Upper = 97.5th percentile
- **Edge qualification**: lower bound of CI > 0 (positive expectancy with 95% confidence)

### Edge Strength Metric

Normalize the expectancy by the CI width to create a signal-to-noise ratio:

```
edge_strength = expectancy / (CI_upper - CI_lower)
```

Higher values = more reliable edges (high signal relative to noise).

### FDR Correction Strategy

- **Method**: Benjamini-Hochberg (BH) procedure
- **Target FDR**: q = 0.10 (default), configurable
- **P-value per combination**: Proportion of bootstrap resamples where expectancy ≤ 0 (one-sided)
- **Procedure**:
  1. Sort all candidate p-values ascending
  2. Find largest k where p_k ≤ (k / m) × q (m = total candidates)
  3. Reject all H0 for i = 1..k
- **Risk**: BH assumes independence or positive correlation. Trade dimensions ARE correlated (e.g., strategies × setups). Consider Benjamini-Yekutieli if correlation is severe.

### Minimum Observations Rule

- **Default**: 30 trades per combination (configurable)
- **Combinations below threshold**: still returned in response with `significant: false` and a `below_min_observations: true` flag
- **Never hidden** — the user should see what was excluded and why

### Stability Test

- **Split**: Chronological 50/50 split by `exit_datetime`
- **Criteria**: Edge qualifies as "stable" if:
  1. Both halves have ≥ min_observations
  2. Both halves have positive expectancy
  3. Expectancy CIs from both halves overlap
- **Result**: `stability: "stable" | "unstable" | "insufficient_data"`

### Traceability

Each ranked edge MUST include:
- `trade_ids: list[int]` — the exact trades that compose this combination
- This enables the frontend to link → trade detail

---

## 5. Risks and Blockers

### Performance Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Bootstrap on 10K resamples × hundreds of combos** | 🔴 High | Vectorize with numpy; cache CI results; make resample count configurable |
| **Loading ALL relations for ALL trades** | 🟡 Medium | Use selective `load_relations` — only load what's needed for the requested dimensions |
| **N+ combinations explosion** | 🟡 Medium | Only enumerate combos that actually exist in the data (not full Cartesian product) |
| **In-memory on large trade sets (10K+ trades)** | 🟡 Medium | Pagination for the trade list endpoint; edge discovery is an analytical batch operation |

### Data Sparsity Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Most combos will have < 30 trades** | 🟡 Medium | Return them with `significant: false`; user sees what's excluded |
| **Single-trade combos from pivot overcounting** | 🟢 Low | `trade_tags` and `mistake_entries` can create misleading combos (one trade → multiple tag groups) — document this clearly |
| **Null FK values (strategy_id = NULL)** | 🟢 Low | Group under "Unknown" as existing breakdowns do |

### Schema Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **`load_relations` does not support `market_session`** | 🟢 Low | Add to `load_relations` whitelist in `list_closed` |
| **`list_closed` has no `direction` filter** | 🟢 Low | Not needed — direction is a group dimension, not a filter |
| **No `market_id` via session** | 🟢 Low | Asset → Market join already exists for `market_id` filter |

### Dependency Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **No numpy/scipy in dependencies** | 🟡 Medium | Add `numpy>=1.26` (bootstrap sampling) — pure Python bootstrap is 10-50× slower |
| **No statistics package for FDR** | 🟢 Low | BH procedure is ~15 lines of Python — no dependency needed |

---

## 6. Recommendation

### Ready for Proposal: **Yes with caveats**

**Caveats**:
1. The `AnalyticsFilter` and `list_closed` need minor extension to support `market_session_id` as a loadable relation
2. The project must add `numpy` as a dependency for performant bootstrap
3. Edge Discovery is COMPUTATIONALLY HEAVY — recommend async background computation with cache or lazy generation (compute on first request, cache for duration of session)
4. The frontend needs entirely new components — the existing `BreakdownTable` shape is insufficient for ranked significance data
5. The combination enumeration strategy must be explicitly decided in design: enumerate existing combos post-hoc (group trades in Python) vs. pre-filter (SQL GROUP BY for base combos, then enrich in Python)

### Proposed File Structure

```
backend/app/modules/analytics/
├── calculators/
│   ├── edge_discovery.py          # NEW: cross-dimension enumeration + grouping
│   ├── bootstrap.py               # NEW: bootstrap CI computation
│   ├── fdr.py                     # NEW: Benjamini-Hochberg correction
│   ├── stability.py               # NEW: split-sample stability test
├── schemas.py                     # EXTEND: add EdgeRanking, EdgeResponse, etc.
├── service.py                     # EXTEND: add get_edge_discovery() method
├── router.py                      # EXTEND: add GET /analytics/edges endpoint

frontend/src/modules/analytics/
├── components/
│   ├── EdgeRankingTable.jsx       # NEW: ranked table with CI + significance
│   ├── EdgeDrillDown.jsx          # NEW: trade list for a selected edge
├── services/analyticsApi.js       # EXTEND: add getEdgeDiscovery()
├── utils/constants.js             # EXTEND: add QUERY_KEYS.edgeDiscovery
```

### Next SDD Phase

**`sdd-design`** — The design phase must resolve:
1. Combination enumeration strategy (SQL vs Python grouping)
2. Bootstrap caching strategy (file cache? in-memory? session-scoped?)
3. Whether edge discovery is synchronous or async (background task with polling?)
4. Frontend information architecture: new page vs. new section on Dashboard?
