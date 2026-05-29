"""ToolRegistry — central catalog of all registered Tools."""
from __future__ import annotations

from typing import Dict, List

from .tool import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def names(self) -> List[str]:
        return sorted(self._tools.keys())
