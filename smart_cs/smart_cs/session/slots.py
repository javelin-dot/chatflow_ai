"""Slot model — typed key-value cells the dialogue collects from the user."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Slot:
    name: str
    value: Optional[Any] = None
    type: str = "text"
    required: bool = False
    description: str = ""
    metadata: dict = field(default_factory=dict)

    def is_set(self) -> bool:
        return self.value is not None
