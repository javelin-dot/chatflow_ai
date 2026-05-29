"""audit — emit one AuditEvent per processed message."""
from __future__ import annotations

from ...governance.audit import AuditLog
from ..state import ProcessingState


class Audit:
    def __init__(self, log: AuditLog) -> None:
        self._log = log

    async def __call__(self, state: ProcessingState) -> ProcessingState:
        msg = state.inbound
        actor = f"{msg.actor.value}:{msg.user_id or msg.session_id}"
        self._log.record(
            tenant_id=msg.tenant_id,
            session_id=msg.session_id,
            actor=actor,
            kind="message",
            payload={
                "channel": msg.channel,
                "text": msg.text,
                "route_skill": state.route_skill,
                "intent": state.intent,
                "intent_score": state.intent_score,
                "replies": state.replies,
                "blocked": state.blocked,
                "handoff_requested": state.handoff_requested,
            },
            ok=state.error is None,
            error=state.error,
        )
        return state
