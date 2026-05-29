"""Tool — a unit of capability an Agent may invoke autonomously.

Tools are distinct from Skills:
- Skills are user-facing dialog capabilities.
- Tools are programmatic capabilities (call API, query DB, etc.) that can be
  exposed to LLMs/Agents — and therefore must be gated. See ToolGuard.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)  # JSON-schema-ish
    tags: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    side_effect: bool = False  # write/mutate vs read-only


class Tool(ABC):
    spec: ToolSpec

    @abstractmethod
    async def call(self, **arguments) -> Any: ...

    @property
    def name(self) -> str:
        return self.spec.name


@dataclass
class ToolInvocation:
    tool: str
    arguments: Dict[str, Any]
    actor: str  # "human:<uid>" or "agent:<id>"
    session_id: Optional[str] = None
    tenant_id: Optional[str] = None
