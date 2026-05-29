"""In-memory FAQ KB: loads a YAML list of {id, question, keywords, answer}.

Matching is intentionally simple — keyword/substring scoring. Replace with
BM25 or vector retrieval as needs grow. Borrowed from the article's
"local clearing first" principle: cheap path before heavyweight LLM.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from ...config.loader import load_yaml
from ..base import KnowledgeBase, KnowledgeBaseFactory
from ..document import Chunk, RetrievalHit


@KnowledgeBaseFactory.register("faq_yaml")
class FAQYamlKB(KnowledgeBase):
    """A keyword-matched FAQ KB backed by a YAML file."""

    def __init__(self, id: str, source: str, base_dir: str | Path | None = None, **_: object) -> None:
        self.id = id
        path = Path(source)
        if not path.is_absolute() and base_dir:
            path = Path(base_dir) / path
        self._entries = self._load(path)

    @staticmethod
    def _load(path: Path) -> List[dict]:
        if not path.exists():
            return []
        data = load_yaml(path)
        if isinstance(data, dict):
            data = data.get("faqs") or []
        if not isinstance(data, list):
            return []
        return [e for e in data if isinstance(e, dict)]

    def search(self, query: str, *, top_k: int = 5) -> List[RetrievalHit]:
        q = (query or "").strip().lower()
        if not q:
            return []
        scored: list[tuple[float, dict]] = []
        for entry in self._entries:
            score = self._score(q, entry)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits: list[RetrievalHit] = []
        for score, entry in scored[:top_k]:
            chunk = Chunk(
                id=entry.get("id", ""),
                document_id=entry.get("id", ""),
                content=entry.get("answer", ""),
                metadata={"question": entry.get("question", "")},
            )
            hits.append(RetrievalHit(chunk=chunk, score=score, kb_id=self.id))
        return hits

    @staticmethod
    def _score(q: str, entry: dict) -> float:
        question = (entry.get("question") or "").lower()
        keywords = [str(k).lower() for k in (entry.get("keywords") or [])]
        if not question and not keywords:
            return 0.0
        # Exact keyword hit wins; substring is a soft hit.
        if any(k and k in q for k in keywords):
            return 1.0
        if question and (question in q or q in question):
            return 0.8
        # Token overlap as a weak signal.
        q_tokens = set(q.split())
        kw_tokens = set(k for k in keywords)
        overlap = len(q_tokens & kw_tokens) / max(len(q_tokens), 1)
        return overlap * 0.5
