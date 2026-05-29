"""Shared primitive types."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class SessionActor(str, Enum):
    """Who is on the user side of the session.

    Borrowed from the article's insight that AI Agent payment volume will dominate;
    we make actor a first-class dimension for routing, throttling, and audit.
    """

    HUMAN = "human"
    AGENT = "agent"
    MIXED = "mixed"


class MessageRole(str, Enum):
    USER = "user"
    BOT = "bot"
    AGENT_HUMAN = "agent_human"
    SYSTEM = "system"


@dataclass
class InboundMessage:
    """Normalized inbound message produced by ChannelGateway."""

    tenant_id: str
    channel: str
    session_id: str
    text: str
    user_id: Optional[str] = None
    actor: SessionActor = SessionActor.HUMAN
    metadata: Dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=utcnow)


@dataclass
class OutboundMessage:
    """Normalized outbound message returned to a channel."""

    tenant_id: str
    channel: str
    session_id: str
    text: str
    role: MessageRole = MessageRole.BOT
    payload: Dict[str, Any] = field(default_factory=dict)
    sent_at: datetime = field(default_factory=utcnow)
