"""Orchestrator — sequential pipeline of nodes.

Phase 0 keeps it as a plain async sequence; nodes are designed so that
Phase 1 can lift them into a LangGraph StateGraph without changing signatures.
"""
from __future__ import annotations

from typing import List, Optional

from ..governance.audit import AuditLog
from ..governance.guardrail import Guardrail
from ..governance.quota import SessionQuota
from ..handoff.manager import HandoffManager
from ..nlu.router import IntentRouter
from ..session.store.base import SessionStore
from ..shared.exceptions import QuotaExceededError
from ..shared.types import InboundMessage, MessageRole, OutboundMessage
from ..skills.skill import Skill
from .nodes.act import Act
from .nodes.audit import Audit
from .nodes.perceive import Perceive
from .nodes.respond import Respond
from .nodes.route import Route
from .state import ProcessingState


class Orchestrator:
    def __init__(
        self,
        *,
        session_store: SessionStore,
        router: IntentRouter,
        skills: List[Skill],
        guardrail: Guardrail,
        audit_log: AuditLog,
        quota: Optional[SessionQuota] = None,
        handoff: Optional[HandoffManager] = None,
    ) -> None:
        self._guardrail = guardrail
        self._audit = audit_log
        self._quota = quota or SessionQuota()
        self._handoff = handoff or HandoffManager()

        skills_by_name = {s.name: s for s in skills}
        self._perceive = Perceive(session_store)
        self._route = Route(router)
        self._act = Act(skills_by_name)
        self._respond = Respond(session_store, guardrail)
        self._audit_node = Audit(audit_log)

    async def handle(self, inbound: InboundMessage) -> OutboundMessage:
        state = ProcessingState(inbound=inbound)

        # Inbound guardrail first — block before doing work.
        gr = self._guardrail.check_inbound(inbound.text)
        if not gr.allowed:
            state.blocked = True
            state.replies = ["抱歉，您的输入包含不允许的内容。"]
            await self._respond(state)
            await self._audit_node(state)
            return self._render(state)

        try:
            await self._perceive(state)
            if state.session is not None:
                self._quota.enforce(state.session)
            await self._route(state)
            await self._act(state)
            if state.handoff_requested and state.session is not None:
                self._handoff.enqueue(
                    tenant_id=state.session.tenant_id,
                    session_id=state.session.id,
                    reason="user_requested" if state.route_skill == "handoff" else "policy",
                )
            await self._respond(state)
        except QuotaExceededError as exc:
            state.error = str(exc)
            state.replies = ["本次会话已达到最大轮次，请稍后再试。"]
        finally:
            await self._audit_node(state)

        return self._render(state)

    def _render(self, state: ProcessingState) -> OutboundMessage:
        text = "\n".join(state.replies) if state.replies else ""
        return OutboundMessage(
            tenant_id=state.inbound.tenant_id,
            channel=state.inbound.channel,
            session_id=state.inbound.session_id,
            text=text,
            role=MessageRole.BOT,
            payload={
                "skill": state.route_skill,
                "intent": state.intent,
                "blocked": state.blocked,
                "handoff": state.handoff_requested,
            },
        )
