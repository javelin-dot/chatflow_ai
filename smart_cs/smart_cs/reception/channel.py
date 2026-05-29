"""Channel abstractions.

A Channel is one concrete way users reach the system (console, REST, WebSocket,
email, IM, voice). InputChannel handles inbound; OutputChannel handles outbound.
Most adapters implement both via one class.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from ..shared.types import InboundMessage, OutboundMessage


class InputChannel(ABC):
    """Source of inbound messages."""

    name: str = "base"

    @abstractmethod
    async def receive(self) -> AsyncIterator[InboundMessage]:  # pragma: no cover
        """Yield inbound messages until the channel closes."""
        if False:
            yield  # type: ignore[unreachable]


class OutputChannel(ABC):
    """Sink of outbound messages."""

    name: str = "base"

    @abstractmethod
    async def send(self, message: OutboundMessage) -> None: ...


class Channel(InputChannel, OutputChannel, ABC):
    """A bidirectional channel."""

    name: str = "base"

    async def open(self) -> None:
        """Optional lifecycle hook."""

    async def close(self) -> None:
        """Optional lifecycle hook."""


class ChannelFactory:
    """Registry to map config 'type' → Channel constructor."""

    _registry: dict = {}

    @classmethod
    def register(cls, name: str):
        def deco(target):
            cls._registry[name] = target
            return target
        return deco

    @classmethod
    def create(cls, name: str, **options) -> Channel:
        if name not in cls._registry:
            raise KeyError(f"Channel type not registered: {name}")
        return cls._registry[name](**options)

    @classmethod
    def known(cls) -> list[str]:
        return sorted(cls._registry.keys())
