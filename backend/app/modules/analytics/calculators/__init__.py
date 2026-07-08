"""Calculator registry — pure function analytics calculators.

Extend by adding a new module and registering it here.
"""

from collections.abc import Callable

CALCULATORS: dict[str, Callable] = {}
