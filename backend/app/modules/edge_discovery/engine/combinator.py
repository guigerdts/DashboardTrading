"""Combinator — enumerates trade groups by dimension combinations.

Pure function: takes a list of trades, returns deduplicated groups
with dimensions, trade_ids, and trades. No side effects.
"""

from __future__ import annotations

from collections import defaultdict

from app.modules.edge_discovery.models import TradeGroup, TradeInput, compute_group_id


class Combinator:
    """Enumerates dimension groups from a list of trades.

    Dimensions: strategy, setup, session, asset, direction.
    Null-safe — missing dimensions are stored as None and treated as
    distinct from any concrete value.
    """

    # Dimension keys (order defines canonical dimension order)
    DIMENSIONS = ("strategy", "setup", "session", "asset", "direction")

    def enumerate(self, trades: list[TradeInput]) -> list[TradeGroup]:
        """Group trades by every non-null dimension combination.

        Builds groups for each individual dimension (univariate) and
        each pair of co-occurring non-null dimensions (bivariate).
        Avoids Cartesian explosion by only creating groups where at
        least 2 trades share the same dimension values.

        Parameters
        ----------
        trades : list[TradeInput]
            Flattened trade inputs.

        Returns
        -------
        list[TradeGroup]
            Deduplicated trade groups.
        """
        if not trades:
            return []

        groups: dict[str, TradeGroup] = {}

        # ── Univariate groups (single dimension) ─────────────────────
        for dim in self.DIMENSIONS:
            buckets: dict[str | None, list[TradeInput]] = defaultdict(list)
            for t in trades:
                val = getattr(t, dim, None)
                buckets[val].append(t)

            for value, bucket in buckets.items():
                if len(bucket) < 2:
                    continue
                dims: dict[str, str | None] = {
                    d: (value if d == dim else None) for d in self.DIMENSIONS
                }
                gid = compute_group_id(dims)
                if gid not in groups:
                    groups[gid] = TradeGroup(
                        group_id=gid,
                        dimensions=dims,
                        trade_ids=sorted(t.id for t in bucket),
                        trades=bucket,
                    )

        # ── Bivariate groups (pairs of co-occurring dimensions) ──────
        for i, dim_a in enumerate(self.DIMENSIONS):
            for dim_b in self.DIMENSIONS[i + 1 :]:
                pair_buckets: dict[tuple[str | None, str | None], list[TradeInput]] = defaultdict(
                    list
                )
                for t in trades:
                    va = getattr(t, dim_a, None)
                    vb = getattr(t, dim_b, None)
                    # Both must be non-null for a meaningful pair group
                    if va is not None and vb is not None:
                        pair_buckets[(va, vb)].append(t)

                for (va, vb), bucket in pair_buckets.items():
                    if len(bucket) < 2:
                        continue
                    dims = {d: None for d in self.DIMENSIONS}
                    dims[dim_a] = va
                    dims[dim_b] = vb
                    gid = compute_group_id(dims)
                    if gid not in groups:
                        groups[gid] = TradeGroup(
                            group_id=gid,
                            dimensions=dims,
                            trade_ids=sorted(t.id for t in bucket),
                            trades=bucket,
                        )

        return list(groups.values())
