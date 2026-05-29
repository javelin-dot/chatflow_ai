"""HandoffManager — minimal queue-based handoff.

Phase 0 stub: prints to stdout and tags the session. Real implementation
integrates with the company's IM (Slack/Lark/dedicated agent desk).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..shared.types import new_id, utcnow


@dataclass
class HandoffTicket:
    id: str
    tenant_id: str
    session_id: str
    reason: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    assigned_to: Optional[str] = None
    closed_at: Optional[datetime] = None


class HandoffManager:
    def __init__(self) -> None:
        self._tickets: List[HandoffTicket] = []

    def enqueue(
        self,
        *,
        tenant_id: str,
        session_id: str,
        reason: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> HandoffTicket:
        t = HandoffTicket(
            id=new_id("ho"),
            tenant_id=tenant_id,
            session_id=session_id,
            reason=reason,
            payload=payload or {},
        )
        self._tickets.append(t)
        return t

    def pending(self) -> List[HandoffTicket]:
        return [t for t in self._tickets if t.closed_at is None]

    def close(self, ticket_id: str) -> None:
        for t in self._tickets:
            if t.id == ticket_id and t.closed_at is None:
                t.closed_at = utcnow()
                return
