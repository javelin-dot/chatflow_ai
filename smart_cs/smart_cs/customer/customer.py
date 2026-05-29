"""Customer model — the human or org on the other side of a session."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Customer:
    id: str
    tenant_id: str
    name: Optional[str] = None
    contacts: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)
