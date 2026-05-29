"""Document and Chunk — the units of knowledge."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    id: str
    title: str = ""
    content: str = ""
    source: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float
    kb_id: str = ""

    @property
    def text(self) -> str:
        return self.chunk.content
