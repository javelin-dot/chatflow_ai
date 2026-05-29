"""Ticket — a work order spawned from a conversation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..shared.types import new_id, utcnow


class TicketStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Ticket:
    id: str
    tenant_id: str
    session_id: Optional[str] = None
    subject: str = ""
    body: str = ""
    status: TicketStatus = TicketStatus.OPEN
    priority: TicketPriority = TicketPriority.NORMAL
    tags: List[str] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


def new_ticket(tenant_id: str, **kw) -> Ticket:
    return Ticket(id=new_id("tkt"), tenant_id=tenant_id, **kw)
