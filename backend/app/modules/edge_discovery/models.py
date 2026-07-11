"""Edge Discovery domain types — pure data structures, no Pydantic.

Holds internal domain types used by the engine layer. Pydantic models
for API I/O live in ``schemas.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Literal

ConfidenceLevel = Literal["high", "medium", "low", "insufficient"]


@dataclass
class TradeInput:
    """Minimal trade representation consumed by the combinator.

    Carries only the fields needed for grouping and scoring. Flattened
    from the full ``Trade`` ORM model before engine processing.
    """

    id: int
    strategy: str | None = None
    setup: str | None = None
    session: str | None = None
    asset: str | None = None
    direction: str | None = None
    exit_datetime: str | None = None
    pnl: float = 0.0
    risk_amount: float | None = None


@dataclass
class TradeGroup:
    """A single edge group produced by the combinator."""

    group_id: str
    dimensions: dict[str, str | None]
    trade_ids: list[int]
    trades: list[TradeInput] = field(default_factory=list)


@dataclass
class EdgeScore:
    """Complete edge score for a single group — the core output type."""

    group_id: str
    dimensions: dict[str, str | None]
    trade_ids: list[int]
    trade_count: int
    expectancy: float
    net_pnl: float
    profit_factor: float | None
    confidence_interval: tuple[float, float]
    p_value: float
    fdr_adjusted_p_value: float
    stability_score: float
    edge_score: float
    confidence_level: ConfidenceLevel
    failure_reasons: list[str]


@dataclass
class SnapshotMeta:
    """Metadata stored alongside an edge snapshot."""

    snapshot_id: str
    created_at: str
    trade_count: int
    group_count: int
    params: dict


def compute_group_id(dimensions: dict[str, str | None]) -> str:
    """Deterministic group ID from a sorted dimension tuple.

    Uses SHA-256 of the canonical JSON representation so the same
    dimension combination always yields the same ID.
    """
    canonical = json.dumps(
        {k: v for k, v in sorted(dimensions.items())},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
