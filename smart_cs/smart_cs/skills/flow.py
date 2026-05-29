"""Flow — YAML-declared multi-step business workflow.

Skeleton for now; aligns with chatflow_ai's Flow shape so a future port is easy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FlowStep:
    id: str
    type: str  # ACTION / COLLECT / CONDITION / LINK / CALL / SET_SLOT / END
    next: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Flow:
    id: str
    description: str = ""
    steps: List[FlowStep] = field(default_factory=list)

    def step(self, step_id: str) -> Optional[FlowStep]:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None
