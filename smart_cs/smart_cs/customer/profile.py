"""CustomerProfile aggregates data across systems (similar to a 360 view)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .customer import Customer


@dataclass
class CustomerProfile:
    customer: Customer
    recent_orders: List[Dict[str, Any]] = field(default_factory=list)
    open_tickets: List[Dict[str, Any]] = field(default_factory=list)
    history_summary: Optional[str] = None
