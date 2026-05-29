"""perceive — bring up the session for this inbound message."""
from __future__ import annotations

from ...session.session import Session
from ...session.store.base import SessionStore
from ..state import ProcessingState


class Perceive:
    def __init__(self, store: SessionStore) -> None:
        self._store = store

    async def __call__(self, state: ProcessingState) -> ProcessingState:
        msg = state.inbound
        session = self._store.get(msg.tenant_id, msg.session_id)
        if session is None:
            session = Session.new(
                tenant_id=msg.tenant_id,
                channel=msg.channel,
                actor=msg.actor,
                user_id=msg.user_id,
                session_id=msg.session_id,
            )
        session.add_user_turn(msg.text)
        state.session = session
        return state
