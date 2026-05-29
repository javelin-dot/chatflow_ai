"""Dialogue turn record."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..shared.types import MessageRole, utcnow


@dataclass
class Turn:
    role: MessageRole
    text: str
    timestamp: datetime = field(default_factory=utcnow)
    skill: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    audit_refs: List[str] = field(default_factory=list)
