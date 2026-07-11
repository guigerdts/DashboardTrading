"""Pydantic schemas for API I/O — Edge Discovery module.

All request/response models used by the router layer.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Request schemas ────────────────────────────────────────────────────────


class EdgeGenerateRequest(BaseModel):
    """Parameters for triggering an edge discovery generation."""

    min_observations: int = Field(default=30, ge=2, description="Minimum trades per group")
    bootstrap_resamples: int = Field(
        default=10_000, ge=100, le=100_000, description="Bootstrap resample count"
    )
    fdr_alpha: float = Field(
        default=0.05, ge=0.01, le=0.50, description="FDR significance threshold"
    )
    stability_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum stability score"
    )
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


# ── Response schemas ───────────────────────────────────────────────────────


class EdgeScore(BaseModel):
    """Single edge score entry in a ranking response."""

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
    confidence_level: Literal["high", "medium", "low", "insufficient"]
    failure_reasons: list[str]


class EdgeRankingResponse(BaseModel):
    """Response containing a full ranked edge discovery result."""

    snapshot_id: str
    total_groups: int
    rankings: list[EdgeScore]


class EdgeDetailResponse(BaseModel):
    """Response with a single edge score detail."""

    snapshot_id: str
    edge: EdgeScore


class TagImpact(BaseModel):
    """Impact of a single tag on edge performance."""

    tag_id: int
    tag_name: str
    trade_count: int
    expectancy: float
    net_pnl: float


class MistakeImpact(BaseModel):
    """Impact of a single mistake on edge performance."""

    mistake_id: int
    mistake_name: str
    trade_count: int
    expectancy: float
    net_pnl: float


class SnapshotInfo(BaseModel):
    """Summary info for a single snapshot in a list."""

    snapshot_id: str
    created_at: str
    trade_count: int
    group_count: int
    params: dict


class SnapshotListResponse(BaseModel):
    """Response listing all available snapshots."""

    snapshots: list[SnapshotInfo]
    total: int
