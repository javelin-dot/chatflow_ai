"""Session aggregates all state for a single conversation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..shared.types import MessageRole, SessionActor, new_id, utcnow
from .slots import Slot
from .stack import DialogueStack, StackFrame
from .turn import Turn


@dataclass
class Session:
    id: str
    tenant_id: str
    workspace_id: str = "default"
    channel: str = "unknown"
    actor: SessionActor = SessionActor.HUMAN
    user_id: Optional[str] = None
    slots: Dict[str, Slot] = field(default_factory=dict)
    stack: DialogueStack = field(default_factory=DialogueStack)
    turns: List[Turn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    closed: bool = False

    @classmethod
    def new(
        cls,
        tenant_id: str,
        *,
        workspace_id: str = "default",
        channel: str = "unknown",
        actor: SessionActor = SessionActor.HUMAN,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "Session":
        return cls(
            id=session_id or new_id("sess"),
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            channel=channel,
            actor=actor,
            user_id=user_id,
        )

    def add_user_turn(self, text: str) -> None:
        self.turns.append(Turn(role=MessageRole.USER, text=text))
        self.updated_at = utcnow()

    def add_bot_turn(self, text: str, *, skill: Optional[str] = None) -> None:
        self.turns.append(Turn(role=MessageRole.BOT, text=text, skill=skill))
        self.updated_at = utcnow()

    def latest_user_text(self) -> str:
        for t in reversed(self.turns):
            if t.role == MessageRole.USER:
                return t.text
        return ""

    def push_frame(self, frame: StackFrame) -> None:
        self.stack.push(frame)
        self.updated_at = utcnow()

    def set_slot(self, name: str, value: Any) -> None:
        slot = self.slots.get(name) or Slot(name=name)
        slot.value = value
        self.slots[name] = slot
        self.updated_at = utcnow()
