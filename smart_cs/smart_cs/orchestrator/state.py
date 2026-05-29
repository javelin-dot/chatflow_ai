"""ProcessingState — the per-message state passed across orchestrator nodes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..knowledge.document import RetrievalHit
    from ..session.session import Session
    from ..shared.types import InboundMessage


@dataclass
class ProcessingState:
    inbound: "InboundMessage"
    session: Optional["Session"] = None
    route_skill: Optional[str] = None
    intent: Optional[str] = None
    intent_score: float = 0.0
    hits: List["RetrievalHit"] = field(default_factory=list)
    replies: List[str] = field(default_factory=list)
    blocked: bool = False
    handoff_requested: bool = False
    error: Optional[str] = None
    audit_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
