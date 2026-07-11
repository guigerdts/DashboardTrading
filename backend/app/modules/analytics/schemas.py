"""Analytics module schemas — request filters and response models."""

from datetime import datetime

from pydantic import BaseModel


class AnalyticsFilter(BaseModel):
    """Common filter schema shared by ALL endpoints. All fields optional."""

    account_id: int | None = None
    asset_id: int | None = None
    market_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    window_size: int | None = None

    def to_filter_kwargs(self) -> dict:
        return {k: v for k, v in self.model_dump(exclude_none=True).items() if k != "window_size"}


class PerformanceMetrics(BaseModel):
    net_pnl: float
    gross_profit: float
    gross_loss: float
    trade_count: int = 0
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_win: float | None = None
    avg_loss: float | None = None
    avg_r_multiple: float | None = None


class RiskMetrics(BaseModel):
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown: float
    current_drawdown_pct: float
    recovery_factor: float | None = None
    payoff_ratio: float | None = None


class SummaryResponse(BaseModel):
    """Aggregated performance + risk metrics."""

    total_trades: int
    total_trades_all: int = 0
    total_open_trades: int = 0
    performance: PerformanceMetrics
    risk: RiskMetrics


class EquityPoint(BaseModel):
    date: datetime | None = None
    equity: float


class StreakInfo(BaseModel):
    current: int = 0
    maximum: int = 0


class Streaks(BaseModel):
    winning_streak: StreakInfo
    losing_streak: StreakInfo


class PnLPeriod(BaseModel):
    period: str
    pnl: float


class EquityResponse(BaseModel):
    total_trades: int
    equity_curve: list[EquityPoint]
    balance_curve: list[EquityPoint]
    streaks: Streaks
    pnl_daily: list[PnLPeriod]
    pnl_weekly: list[PnLPeriod]
    pnl_monthly: list[PnLPeriod]


class PerformanceResponse(BaseModel):
    total_trades: int
    performance: PerformanceMetrics


class AssetBreakdown(BaseModel):
    asset_id: int
    symbol: str
    trade_count: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_win: float | None = None
    avg_loss: float | None = None


class AssetBreakdownResponse(BaseModel):
    total_trades: int
    assets: list[AssetBreakdown]


class DirectionBreakdownResponse(BaseModel):
    total_trades: int
    long: PerformanceMetrics
    short: PerformanceMetrics


class MarketBreakdown(BaseModel):
    market_id: int
    trade_count: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate: float
    profit_factor: float | None = None
    expectancy: float


class MarketBreakdownResponse(BaseModel):
    total_trades: int
    markets: list[MarketBreakdown]


class BreakdownItem(BaseModel):
    """Common breakdown contract shared by all 4 breakdown endpoints."""

    id: int
    name: str
    trade_count: int
    win_rate: float
    net_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None = None
    expectancy: float
    avg_win: float | None = None
    avg_loss: float | None = None


class BreakdownResponse(BaseModel):
    items: list[BreakdownItem]


class RDistributionItem(BaseModel):
    bucket: str
    count: int


class RDistributionResponse(BaseModel):
    total_trades: int
    buckets: list[RDistributionItem]
    trades_without_risk: int = 0


class HeatmapItem(BaseModel):
    day: int
    hour: int
    trade_count: int
    net_pnl: float


class HeatmapResponse(BaseModel):
    total_trades: int
    cells: list[HeatmapItem]


# =========================================================================
# Rolling windowed metrics
# =========================================================================


class RollingPoint(BaseModel):
    """A single data point in the rolling metrics series."""

    index: int
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_r_multiple: float | None = None
    trade_count: int


class RollingResponse(BaseModel):
    """Rolling windowed metrics response."""

    window_size: int
    points: list[RollingPoint]


# =========================================================================
# Performance by period
# =========================================================================


class PerformanceByPeriodRecord(BaseModel):
    """Performance metrics for a single period."""

    period: str
    trade_count: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_r_multiple: float | None = None


class PerformanceByPeriodResponse(BaseModel):
    """Performance grouped by calendar period."""

    records: list[PerformanceByPeriodRecord]


# =========================================================================
# Period comparison
# =========================================================================


class ComparePeriodsResponse(BaseModel):
    """Comparison of two arbitrary date ranges with delta and delta_percent.

    ``delta`` uses ``period_a`` as the minuend (period_a - period_b).
    ``delta_percent`` uses ``period_a`` as the base — null when base is 0.
    """

    period_a: PerformanceByPeriodRecord
    period_b: PerformanceByPeriodRecord
    delta: PerformanceByPeriodRecord
    delta_percent: PerformanceByPeriodRecord
