"""get_logger — central logger factory."""
from __future__ import annotations

import logging
import sys
from typing import Optional

_CONFIGURED = False


def _configure_root(level: int) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
    )
    root = logging.getLogger("smart_cs")
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    _configure_root(level or logging.INFO)
    return logging.getLogger(f"smart_cs.{name}" if not name.startswith("smart_cs") else name)
