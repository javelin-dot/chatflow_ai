"""respond — finalize and persist the bot turn."""
from __future__ import annotations

from ...governance.guardrail import Guardrail
from ...session.store.base import SessionStore
from ..state import ProcessingState


class Respond:
    def __init__(self, store: SessionStore, guardrail: Guardrail) -> None:
        self._store = store
        self._guardrail = guardrail

    async def __call__(self, state: ProcessingState) -> ProcessingState:
        filtered: list[str] = []
        for text in state.replies:
            check = self._guardrail.check_outbound(text)
            if check.allowed:
                filtered.append(text)
            else:
                state.blocked = True
                filtered.append("（系统已拦截一段不合规的回复）")
        state.replies = filtered

        if state.session is not None:
            for text in filtered:
                state.session.add_bot_turn(text, skill=state.route_skill)
            self._store.save(state.session)
        return state
