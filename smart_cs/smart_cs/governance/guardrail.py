"""Guardrail — inbound/outbound content moderation.

Phase 0: pattern-based block list. Phase 1: pluggable LLM moderation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern


@dataclass
class GuardrailResult:
    allowed: bool
    reason: Optional[str] = None
    redacted_text: Optional[str] = None


class Guardrail:
    def __init__(self, block_patterns: Optional[List[str]] = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self._patterns: List[Pattern[str]] = [re.compile(p) for p in (block_patterns or [])]

    def check_inbound(self, text: str) -> GuardrailResult:
        if not self.enabled:
            return GuardrailResult(allowed=True)
        for p in self._patterns:
            if p.search(text):
                return GuardrailResult(
                    allowed=False,
                    reason=f"matched block pattern: {p.pattern}",
                )
        return GuardrailResult(allowed=True)

    def check_outbound(self, text: str) -> GuardrailResult:
        return self.check_inbound(text)
