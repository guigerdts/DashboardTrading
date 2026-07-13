"""Cross-asset correlation calculator — pure function.

Computes Pearson correlation between asset pairs based on daily PnL.
Only pairs with sufficient shared trading days (>= min_trades) produce
a correlation value; others are returned as ``None``.
"""

import math
from collections import defaultdict
from datetime import datetime

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def _to_date(val: str | datetime | None) -> str | None:
    """Extract YYYY-MM-DD date key from an ISO string or datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        return val[:10]
    return None


def _daily_pnl(trades: list[Trade]) -> dict[str, float]:
    """Group trades by exit date and sum PnL per day."""
    daily: dict[str, float] = defaultdict(float)
    for t in trades:
        date_key = _to_date(t.exit_datetime or t.entry_datetime)
        if date_key:
            daily[date_key] += compute_pnl(t)
    return dict(daily)


def _pearson_r(x: list[float], y: list[float]) -> float | None:
    """Compute Pearson correlation coefficient between two paired arrays."""
    n = len(x)
    if n < 2:
        return None

    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)
    sum_y2 = sum(yi * yi for yi in y)

    numerator = n * sum_xy - sum_x * sum_y
    denom_x = n * sum_x2 - sum_x * sum_x
    denom_y = n * sum_y2 - sum_y * sum_y

    if denom_x <= 0 or denom_y <= 0:
        return None

    denominator = math.sqrt(denom_x * denom_y)
    if denominator == 0:
        return None

    return numerator / denominator


def compute_correlation(trades: list[Trade], min_trades: int = 30) -> list[dict]:
    """Compute Pearson correlation between asset pairs.

    For each pair of assets, trades are grouped by exit date into daily PnL.
    Only dates where both assets have trades contribute to the correlation.
    Pairs with fewer than ``min_trades`` shared dates produce ``correlation=None``.

    Returns an empty list when there are fewer than 2 distinct assets.
    """
    if not trades:
        return []

    # Group trades by asset_id
    asset_trades: dict[int, list[Trade]] = defaultdict(list)
    asset_names: dict[int, str | None] = {}
    for t in trades:
        asset_trades[t.asset_id].append(t)
        if t.asset_id not in asset_names:
            asset_names[t.asset_id] = t.asset.name if t.asset else None

    asset_ids = list(asset_trades.keys())
    if len(asset_ids) < 2:
        return []

    # Pre-compute daily PnL per asset
    asset_daily: dict[int, dict[str, float]] = {}
    for aid in asset_ids:
        asset_daily[aid] = _daily_pnl(asset_trades[aid])

    results: list[dict] = []

    for i in range(len(asset_ids)):
        for j in range(i + 1, len(asset_ids)):
            aid, bid = asset_ids[i], asset_ids[j]

            a_daily = asset_daily[aid]
            b_daily = asset_daily[bid]

            # Find shared dates (daily PnL intersection)
            common_dates = sorted(set(a_daily.keys()) & set(b_daily.keys()))
            trade_count = len(common_dates)

            if trade_count < min_trades:
                results.append(
                    {
                        "asset_a_id": aid,
                        "asset_a_name": asset_names.get(aid),
                        "asset_b_id": bid,
                        "asset_b_name": asset_names.get(bid),
                        "correlation": None,
                        "trade_count": trade_count,
                    }
                )
                continue

            x_vals = [a_daily[d] for d in common_dates]
            y_vals = [b_daily[d] for d in common_dates]

            r = _pearson_r(x_vals, y_vals)
            correlation = round(r, 4) if r is not None else None

            results.append(
                {
                    "asset_a_id": aid,
                    "asset_a_name": asset_names.get(aid),
                    "asset_b_id": bid,
                    "asset_b_name": asset_names.get(bid),
                    "correlation": correlation,
                    "trade_count": trade_count,
                }
            )

    return results
