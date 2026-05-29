"""Multi-KB Retriever — fans out to all KBs and merges hits."""
from __future__ import annotations

from typing import List

from .base import KnowledgeBase
from .document import RetrievalHit


class Retriever:
    def __init__(self, kbs: List[KnowledgeBase]) -> None:
        self._kbs = list(kbs)

    def add(self, kb: KnowledgeBase) -> None:
        self._kbs.append(kb)

    def search(self, query: str, *, top_k: int = 5) -> List[RetrievalHit]:
        merged: List[RetrievalHit] = []
        for kb in self._kbs:
            merged.extend(kb.search(query, top_k=top_k))
        merged.sort(key=lambda h: h.score, reverse=True)
        return merged[:top_k]
