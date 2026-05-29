"""IntentRouter — pick the next skill for a turn.

Phase-0 implementation is rule-based:
  1) Explicit handoff keywords win.
  2) Otherwise, run retrieval over KBs; if score >= threshold, route to
     `faq_answer`.
  3) Else fall back to `fallback`.

Phase-1 swaps in an LLM-backed router (Command generator). This module owns
that decision so other modules don't have to grow LLM dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..knowledge.document import RetrievalHit
from ..knowledge.retriever import Retriever
from ..skills.builtin.handoff import Handoff


@dataclass
class RouteDecision:
    skill: str
    hits: List[RetrievalHit]
    intent: Optional[str] = None
    score: float = 0.0


class IntentRouter:
    def __init__(
        self,
        retriever: Retriever,
        *,
        faq_threshold: float = 0.4,
        enabled_skills: Optional[List[str]] = None,
    ) -> None:
        self._retriever = retriever
        self._threshold = faq_threshold
        self._enabled = set(enabled_skills or [])

    def _is_enabled(self, name: str) -> bool:
        return not self._enabled or name in self._enabled

    def route(self, text: str) -> RouteDecision:
        if self._is_enabled("handoff") and Handoff.detects(text):
            return RouteDecision(skill="handoff", hits=[], intent="handoff", score=1.0)

        hits = self._retriever.search(text, top_k=3)
        if (
            self._is_enabled("faq_answer")
            and hits
            and hits[0].score >= self._threshold
        ):
            return RouteDecision(
                skill="faq_answer",
                hits=hits,
                intent="faq",
                score=hits[0].score,
            )

        return RouteDecision(skill="fallback", hits=hits, intent="fallback", score=0.0)
