"""KnowledgeBase abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .document import RetrievalHit


class KnowledgeBase(ABC):
    """A logical knowledge source.

    Implementations: FAQ YAML, document store, vector store, business API.
    """

    id: str = "base"

    @abstractmethod
    def search(self, query: str, *, top_k: int = 5) -> List[RetrievalHit]: ...


class KnowledgeBaseFactory:
    _registry: dict = {}

    @classmethod
    def register(cls, name: str):
        def deco(target):
            cls._registry[name] = target
            return target
        return deco

    @classmethod
    def create(cls, type_: str, **kwargs) -> KnowledgeBase:
        if type_ not in cls._registry:
            raise KeyError(f"KB type not registered: {type_}")
        return cls._registry[type_](**kwargs)

    @classmethod
    def known(cls) -> list[str]:
        return sorted(cls._registry.keys())
