"""ChannelGateway — unified inbound entry that normalizes any channel event
into an InboundMessage and dispatches to the orchestrator.

Borrowed metaphor: WorldFirst's 'one API for 300+ local payment methods' →
one orchestrator behind N channel adapters.
"""
from __future__ import annotations

from typing import Awaitable, Callable, List

from ..shared.types import InboundMessage, OutboundMessage
from .channel import Channel

Handler = Callable[[InboundMessage], Awaitable[OutboundMessage]]


class ChannelGateway:
    def __init__(self, handler: Handler) -> None:
        self._handler = handler
        self._channels: List[Channel] = []

    def attach(self, channel: Channel) -> None:
        self._channels.append(channel)

    async def serve_one(self, channel: Channel) -> None:
        """Drive a single channel: receive → handle → send loop."""
        await channel.open()
        try:
            async for inbound in channel.receive():
                outbound = await self._handler(inbound)
                await channel.send(outbound)
        finally:
            await channel.close()
