"""SessionStore abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..session import Session


class SessionStore(ABC):
    @abstractmethod
    def get(self, tenant_id: str, session_id: str) -> Optional[Session]: ...

    @abstractmethod
    def save(self, session: Session) -> None: ...

    @abstractmethod
    def delete(self, tenant_id: str, session_id: str) -> None: ...
