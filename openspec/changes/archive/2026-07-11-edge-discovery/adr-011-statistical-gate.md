# ADR-011: Statistical Gate for Edge Exposure

## Status

Accepted

## Context

Edge Discovery enumerates all observed dimension combinations and computes scores for each. Without statistical rigor, the system would surface every combination as an "edge", including:
- Groups with 2 trades that happened to win (noise, not signal)
- Groups where the confidence interval spans zero (not reliably positive)
- Groups that fail multiple comparison correction (false positives from testing hundreds of combinations)
- Groups where the edge exists only in one half of the data (unstable, likely overfitted)

Existing analytics breakdowns show ALL groups regardless of statistical significance. Edge Discovery must be different — it MUST only surface results that pass a rigorous statistical gate, because the entire value proposition is "find edges that are real, not artifacts of noise".

However, we also MUST NOT delete the data — traders need visibility into what was excluded and why, both for trust and for debugging.

## Decision

Every generated `EdgeScore` record is evaluated against four statistical criteria. The result drives a `confidence_level` field and default visibility.

### The Four Gates

A group passes the statistical gate if ALL of the following are true:

1. **Minimum observations**: `trade_count >= min_observations` (default: 30, configurable)
2. **Positive expectancy with confidence**: Bootstrap 95% CI lower bound > 0
3. **FDR pass**: `fdr_adjusted_p_value <= fdr_alpha` (default: 0.10)
4. **Stability threshold**: `stability_score >= stability_threshold` (default: 0.5)

### Confidence Level Mapping

| Condition | confidence_level |
|-----------|-----------------|
| Fails ANY of the 4 gates | `insufficient` |
| Passes all 4 gates AND `stability_score >= 0.8` | `high` |
| Passes all 4 gates AND `0.5 <= stability_score < 0.8` | `medium` |
| Passes all 4 gates AND `stability_score < 0.5` (≥ threshold) | `low` |

### Visibility Rules

| confidence_level | Default in `GET /analytics/edges` | Accessible via `show_insufficient=true` |
|-----------------|-----------------------------------|----------------------------------------|
| `high` | ✅ Shown | — |
| `medium` | ✅ Shown | — |
| `low` | ✅ Shown | — |
| `insufficient` | ❌ Hidden | ✅ Yes |

### Data Retention

- Groups that fail the gate are **never deleted** from the snapshot.
- They are stored in the `results` JSON in the SQLite cache, same as passing groups.
- The `confidence_level: "insufficient"` field, plus individual failure reasons, are available for debugging.
- Admin/advanced endpoints MAY accept `show_insufficient: bool` (default `false`) to reveal filtered groups.
- The `GET /analytics/edges/{group_id}` endpoint returns ANY group, including insufficient ones, for drill-down access.

### Why Not Just Filter at Query Time

- **Reproducibility**: a snapshot's results are immutable. If we filtered at query time, different queries with different gate parameters would see different results from the same snapshot. Storing all results and filtering on read is more transparent.
- **Debugging**: traders can ask "why was this group excluded?" and see the exact failing criterion.
- **Parameter changes**: if `min_observations` is lowered from 30 to 20, we re-generate — we don't re-interpret old snapshots.

### Implementation

The gate is a pure function in the scoring pipeline:

```python
def determine_confidence_level(
    trade_count: int,
    ci_lower: float,
    fdr_adjusted_p_value: float,
    stability_score: float,
    min_observations: int = 30,
    fdr_alpha: float = 0.10,
    stability_threshold: float = 0.5,
) -> tuple[str, list[str]]:
    """Returns (confidence_level, failure_reasons).

    confidence_level is one of 'high', 'medium', 'low', 'insufficient'.
    failure_reasons is a list of human-readable strings for debugging.
    """
    failures = []

    if trade_count < min_observations:
        failures.append(f"trade_count ({trade_count}) < min_observations ({min_observations})")
    if ci_lower <= 0:
        failures.append(f"CI lower bound ({ci_lower}) <= 0")
    if fdr_adjusted_p_value > fdr_alpha:
        failures.append(f"FDR p-value ({fdr_adjusted_p_value}) > alpha ({fdr_alpha})")
    if stability_score < stability_threshold:
        failures.append(f"stability ({stability_score}) < threshold ({stability_threshold})")

    if failures:
        return "insufficient", failures

    if stability_score >= 0.8:
        return "high", []
    elif stability_score >= 0.5:
        return "medium", []
    else:
        return "low", []
```

## Consequences

### Positive

- ✅ **No false discoveries exposed by default** — every surfaced edge has passed minimum observations, positive CI, FDR correction, and stability validation.
- ✅ **Full transparency** — excluded groups are not deleted. Anyone with access to the snapshot can see what was filtered and why. This builds trust.
- ✅ **Configurable rigor** — `min_observations`, `fdr_alpha`, and `stability_threshold` are all parameters on the POST generate endpoint. Teams with fewer trades can lower thresholds; teams with more can raise them.
- ✅ **Graduated confidence** — `high`/`medium`/`low` gives traders a nuanced view rather than a binary "edge / not edge". A `high` edge with stability > 0.8 is far more actionable than a `low` edge barely passing the gate.
- ✅ **Pure function** — the gate has zero dependencies and is trivially unit-testable.

### Negative

- ❌ **Conservative by default** — 30 minimum observations + 0.10 FDR + 0.5 stability means that for small trade databases (< 300 trades), most groups will be `insufficient`. This is correct behavior (the system should not overclaim), but may frustrate early users. Mitigation: the parameters are configurable, documented, and the UI shows the threshold values alongside the data.
- ❌ **FDR assumes independence** — the Benjamini-Hochberg procedure assumes p-values are independent or positively correlated. Trade dimensions ARE correlated (e.g., strategy × setup × direction). BH may be slightly too liberal (under-corrects) under dependency. Benjamini-Yekutieli would be more conservative but also more computationally expensive. Mitigation: document this assumption in the UI; consider BY as a future enhancement if false positives become an issue.
- ❌ **Stability threshold is arbitrary** — 0.5 is a sensible default (better than random) but has no theoretical basis. Different trade styles may need different thresholds. Mitigation: documented as a configurable parameter; future versions could learn the threshold from data.
