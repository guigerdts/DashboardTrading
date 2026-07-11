"""Rule engine — abstract base and auto-registration via RULE_REGISTRY.

Each rule module appends its rule instance to ``RULE_REGISTRY`` at import
time. The engine iterates the registry to collect all active rules.

Importing from this package automatically loads every rule module so that
their ``RULE_REGISTRY.append()`` calls execute at import time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.ai_insights.schemas import Insight, InsightContext


class BaseRule(ABC):
    """Interface for a single deterministic insight rule.

    Subclasses implement ``evaluate()`` which receives the full evaluation
    context and returns either an ``Insight`` or ``None`` when no insight
    applies.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique rule identifier (used as insight ``id``)."""

    @abstractmethod
    def evaluate(self, context: InsightContext) -> Insight | None:
        """Evaluate this rule against the given context.

        Returns an ``Insight`` when the rule fires, or ``None`` when no
        insight currently applies.
        """


# Auto-registry: every rule module appends its instance here at import time.
RULE_REGISTRY: list[BaseRule] = []

# ── Load all rule modules so their RULE_REGISTRY.append() runs ─────────────
# Each module is imported to trigger its side-effect registration.
from . import (  # noqa: F401, E402
    concentration_risk,
    drawdown_risk,
    edge_insufficient,
    edge_significance,
    profit_factor_health,
    win_rate_trend,
)
