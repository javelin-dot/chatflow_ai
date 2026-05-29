# -*- coding: utf-8 -*-
"""Persistent storage for OpenAPI service registry specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from chatflow_ai.integrations.registry import ServiceSpec


class RegistryStorage:
    """JSON file storage for registered service specs."""

    def __init__(self, base_dir: str | None = None) -> None:
        if base_dir is None:
            base_dir = str(Path.home() / ".chatflow" / "registry")
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, spec: ServiceSpec) -> None:
        path = self.base_dir / f"{spec.name}.json"
        data = {
            "name": spec.name,
            "spec": spec.spec,
            "base_url": spec.base_url,
            "token_env": spec.token_env,
            "token_header": spec.token_header,
            "token_prefix": spec.token_prefix,
            "timeout": spec.timeout,
            "default_headers": spec.default_headers,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, name: str) -> Optional[ServiceSpec]:
        path = self.base_dir / f"{name}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ServiceSpec(
            name=data["name"],
            spec=data["spec"],
            base_url=data.get("base_url"),
            token_env=data.get("token_env"),
            token_header=data.get("token_header", "Authorization"),
            token_prefix=data.get("token_prefix", "Bearer "),
            timeout=data.get("timeout", 30.0),
            default_headers=data.get("default_headers", {}),
        )

    def list_names(self) -> List[str]:
        return [path.stem for path in self.base_dir.glob("*.json")]

    def delete(self, name: str) -> bool:
        path = self.base_dir / f"{name}.json"
        if not path.exists():
            return False
        path.unlink()
        return True
