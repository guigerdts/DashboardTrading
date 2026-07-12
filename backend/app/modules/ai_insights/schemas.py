"""Pydantic schemas for AI Insights engine — evaluation inputs and outputs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ── Request filters ────────────────────────────────────────────────────────


class InsightsFilter(BaseModel):
    """Filter params for AI Insights evaluation. All fields optional."""

    account_id: int | None = None
    asset_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    strategy: str | None = None
    setup: str | None = None

    def to_filters(self) -> dict:
        """Drop ``None`` fields — service expects a plain dict."""
        return {k: v for k, v in self.model_dump(exclude_none=True).items()}


# ── Metric / Insight schemas ──────────────────────────────────────────────


class SupportingMetric(BaseModel):
    """A single quantitative metric supporting an insight."""

    name: str
    value: float
    source: str  # "analytics" | "risk" | "edge"
    endpoint: str


class Insight(BaseModel):
    """A single evaluated insight from one rule."""

    id: str
    category: str
    severity: str  # "info" | "warning" | "critical"
    title: str
    message: str
    supporting_metrics: list[SupportingMetric] = []
    trade_ids: list[int] = []
    confidence: str  # "high" | "medium" | "low" | "insufficient"
    recommendation: str | None = None


# ── Context snapshot ──────────────────────────────────────────────────────


class InsightContext(BaseModel):
    """Complete evaluation context assembled from all data sources."""

    filters: dict = {}
    performance: dict | None = None
    risk_metrics: dict | None = None
    exposure: list | None = None
    correlation: dict | None = None
    edge_rankings: list | None = None
    edge_detail: dict | None = None


# ── Response models ───────────────────────────────────────────────────────


class SummaryResponse(BaseModel):
    """Aggregated listing of all current insights."""

    total_count: int
    by_severity: dict
    insights: list[Insight]
    generated_at: datetime
    confidence: str = "high"


class DetailResponse(BaseModel):
    """Single insight with the context snapshot that produced it."""

    insight: Insight
    context_snapshot: dict
    evaluated_at: datetime
