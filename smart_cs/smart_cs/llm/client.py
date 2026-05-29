"""LLMClient — vendor-agnostic chat completion abstraction.

Phase 0 ships an abstract base + an EchoLLM stub usable in tests.
Phase 1 wires OpenAI / Anthropic / DashScope adapters.

Borrowed from chatflow_ai's LLMClient pattern: isolating vendor differences
(Qwen thinking mode, Azure api_version, Anthropic system message placement)
behind one interface so policies/routers stay vendor-neutral.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    content: str
    raw: Any = None
    usage: Dict[str, int] = field(default_factory=dict)


class LLMClient(ABC):
    provider: str = "base"
    model: str = ""

    @abstractmethod
    async def chat(self, messages: List[ChatMessage], **opts) -> ChatResponse: ...


class EchoLLM(LLMClient):
    """A no-network stub: echoes the last user message. Useful for tests."""

    provider = "echo"
    model = "echo-1"

    async def chat(self, messages: List[ChatMessage], **opts) -> ChatResponse:
        last = next((m for m in reversed(messages) if m.role == "user"), None)
        text = last.content if last else ""
        return ChatResponse(content=f"echo: {text}")
