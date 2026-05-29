"""In-memory SessionStore. Default for dev; not durable."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from ..session import Session
from .base import SessionStore


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._data: Dict[Tuple[str, str], Session] = {}

    def get(self, tenant_id: str, session_id: str) -> Optional[Session]:
        return self._data.get((tenant_id, session_id))

    def save(self, session: Session) -> None:
        self._data[(session.tenant_id, session.id)] = session

    def delete(self, tenant_id: str, session_id: str) -> None:
        self._data.pop((tenant_id, session_id), None)
