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

    def to_filter_kwargs(self) -> dict:
        return self.model_dump(exclude_none=True)


class PerformanceMetrics(BaseModel):
    net_pnl: float
    gross_profit: float
    gross_loss: float
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
