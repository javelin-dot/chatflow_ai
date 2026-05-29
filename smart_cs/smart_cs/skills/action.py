"""Action — a single executable step inside a Flow."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..session.session import Session


@dataclass
class ActionResult:
    replies: List[str] = field(default_factory=list)
    slot_updates: Dict[str, Any] = field(default_factory=dict)
    next_action: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)


class Action(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, session: "Session", **kwargs) -> ActionResult: ...
