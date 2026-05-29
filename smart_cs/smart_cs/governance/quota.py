"""Session-level quota: cap max turns to defend against runaway loops.

Tool-level quota lives in skills/tools/guard.py (per VCC card).
"""
from __future__ import annotations

from ..shared.exceptions import QuotaExceededError
from ..session.session import Session


class SessionQuota:
    def __init__(self, max_turns: int = 100) -> None:
        self.max_turns = max_turns

    def enforce(self, session: Session) -> None:
        if self.max_turns and len(session.turns) >= self.max_turns:
            raise QuotaExceededError(
                f"session {session.id} exceeded max_turns={self.max_turns}"
            )
