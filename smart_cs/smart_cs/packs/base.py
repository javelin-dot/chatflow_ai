"""BusinessPack — pluggable industry bundle.

Inspired by WorldFirst's ecosystem composition (WorldFirst + Alipay+ + Antom +
Bettr): the base stays generic, while industry capabilities are shipped as
optional packs that register skills, tools, channels, KBs, guardrail rules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PackManifest:
    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class BusinessPack(ABC):
    """Subclass to define an industry-specific bundle of capabilities."""

    manifest: PackManifest

    @abstractmethod
    def register(self) -> None:
        """Register skills/tools/channels/kbs/guardrails into global registries."""
