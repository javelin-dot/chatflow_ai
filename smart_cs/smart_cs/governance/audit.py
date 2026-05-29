"""AuditLog — structured audit events for the "控" pillar."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TextIO

from ..shared.types import new_id, utcnow


@dataclass
class AuditEvent:
    id: str
    tenant_id: str
    session_id: Optional[str]
    actor: str  # "human:<uid>" or "agent:<id>"
    kind: str  # "inbound" / "outbound" / "tool_call" / "handoff" / "skill_run" / "guardrail_block"
    payload: Dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None
    at: datetime = field(default_factory=utcnow)


class AuditSink:
    def write(self, event: AuditEvent) -> None:  # pragma: no cover
        raise NotImplementedError


class StdoutAuditSink(AuditSink):
    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout

    def write(self, event: AuditEvent) -> None:
        data = asdict(event)
        data["at"] = event.at.isoformat()
        self._stream.write("[audit] " + json.dumps(data, ensure_ascii=False) + "\n")


class InMemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: List[AuditEvent] = []

    def write(self, event: AuditEvent) -> None:
        self.events.append(event)


class AuditLog:
    def __init__(self, sink: AuditSink | None = None, enabled: bool = True) -> None:
        self._sink = sink or StdoutAuditSink()
        self.enabled = enabled

    def record(
        self,
        *,
        tenant_id: str,
        kind: str,
        actor: str = "system",
        session_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        ok: bool = True,
        error: Optional[str] = None,
    ) -> Optional[AuditEvent]:
        if not self.enabled:
            return None
        event = AuditEvent(
            id=new_id("aud"),
            tenant_id=tenant_id,
            session_id=session_id,
            actor=actor,
            kind=kind,
            payload=payload or {},
            ok=ok,
            error=error,
        )
        self._sink.write(event)
        return event


def make_audit_sink(name: str) -> AuditSink:
    if name in ("stdout", "stderr"):
        return StdoutAuditSink(sys.stderr if name == "stderr" else sys.stdout)
    if name == "memory":
        return InMemoryAuditSink()
    raise ValueError(f"unknown audit sink: {name}")
