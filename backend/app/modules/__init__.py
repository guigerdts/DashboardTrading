"""Pluggable module discovery for the Trade Intelligence Platform.

Adding a new backend module requires only creating a new package under
``app/modules/`` with a ``router.py`` that exposes a ``router`` attribute.
Zero changes to existing files (C6).
"""

import importlib
import logging
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)

_MODULES_PATH = Path(__file__).parent

# Directories that should NOT be treated as modules.
_SKIP_DIRS: set[str] = {"__pycache__", "__init__"}


def discover_modules() -> list[APIRouter]:
    """Scan the modules directory and auto-register every subpackage router.

    For each subdirectory that contains a ``router.py``, the function
    imports ``app.modules.<name>.router`` and appends ``router.router``
    to the returned list.

    Ignores:
    - Non-directory entries (files, symlinks)
    - Hidden directories (starting with ``.``)
    - Directories without a ``router.py`` file
    - Known non-module directories (``__pycache__``, ``__init__``)

    Import errors are logged and the broken module is silently skipped.
    The application continues to function with the remaining modules.

    Returns:
        A list of discovered ``APIRouter`` instances, one per module.
    """
    routers: list[APIRouter] = []
    for entry in sorted(_MODULES_PATH.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in _SKIP_DIRS:
            continue
        if not (entry / "router.py").exists():
            continue

        module_path = f"app.modules.{entry.name}.router"
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            logger.exception("Failed to import module %r — skipping", module_path)
            continue

        if not hasattr(mod, "router"):
            logger.warning("Module %r has no 'router' attribute — skipping", module_path)
            continue

        routers.append(mod.router)
        logger.debug("Discovered module: %s", entry.name)

    logger.info("Discovered %d backend module(s)", len(routers))
    return routers
