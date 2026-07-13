"""Engine version auto-capture for Strategy Lab reproducibility.

Must NOT fail silently — run creation requires a valid engine version.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def get_engine_version() -> str:
    """Auto-capture analytics engine version for reproducibility.

    Strategy
    --------
    1. Try ``importlib.metadata.version('tip-backend')``
    2. Fallback: ``git describe --always --dirty --long``
    3. If both fail: raise ``RuntimeError``

    Returns
    -------
    str
        Package version or git describe output.

    Raises
    ------
    RuntimeError
        When neither package metadata nor git is available.
    """
    # Method 1: package version
    try:
        from importlib.metadata import version

        return version("tip-backend")
    except Exception:
        pass

    # Method 2: git
    try:
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty", "--long"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    raise RuntimeError(
        "Cannot determine analytics engine version. "
        "Run creation requires a valid engine version for reproducibility."
    )
