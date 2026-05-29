"""YAML loader with `${VAR:default}` interpolation."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml

_VAR_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::([^}]*))?\}")


def _interpolate(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: "re.Match[str]") -> str:
            name, default = m.group(1), m.group(2) or ""
            return os.environ.get(name, default)
        return _VAR_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interpolate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v) for v in value]
    return value


def load_yaml(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _interpolate(raw)
