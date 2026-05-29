"""Skill — a user-facing capability unit.

A Skill takes a SkillContext (session, retrieved knowledge, current intent
metadata) and returns a SkillResult (zero or more outbound replies, optional
slot updates, optional next skill, optional handoff signal).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..knowledge.document import RetrievalHit
    from ..session.session import Session


@dataclass
class SkillContext:
    session: "Session"
    user_text: str
    hits: List["RetrievalHit"] = field(default_factory=list)
    intent: Optional[str] = None
    intent_score: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    replies: List[str] = field(default_factory=list)
    slot_updates: Dict[str, Any] = field(default_factory=dict)
    next_skill: Optional[str] = None
    handoff: bool = False
    end_session: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def reply(cls, text: str, **kw) -> "SkillResult":
        return cls(replies=[text], **kw)

    @classmethod
    def empty(cls) -> "SkillResult":
        return cls()


class Skill(ABC):
    """Base class for all skills."""

    name: str = "base"
    description: str = ""
    triggers: List[str] = []  # keyword triggers (optional)

    @abstractmethod
    async def run(self, ctx: SkillContext) -> SkillResult: ...


class SkillRegistry:
    _registry: Dict[str, type] = {}

    @classmethod
    def register(cls, target: type | None = None, *, name: Optional[str] = None):
        def deco(klass: type) -> type:
            key = name or getattr(klass, "name", None) or klass.__name__
            cls._registry[key] = klass
            return klass
        if target is not None and isinstance(target, type):
            return deco(target)
        return deco

    @classmethod
    def create(cls, name: str, **kwargs) -> Skill:
        if name not in cls._registry:
            raise KeyError(f"Skill not registered: {name}")
        return cls._registry[name](**kwargs)

    @classmethod
    def known(cls) -> List[str]:
        return sorted(cls._registry.keys())
