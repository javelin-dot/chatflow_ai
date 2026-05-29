"""ConsoleChannel — interactive shell. Used by `smart-cs shell`."""
from __future__ import annotations

import asyncio
import sys
from typing import AsyncIterator, Optional

from ...shared.constants import DEFAULT_TENANT_ID
from ...shared.types import InboundMessage, OutboundMessage, SessionActor
from ..channel import Channel, ChannelFactory


@ChannelFactory.register("console")
class ConsoleChannel(Channel):
    name = "console"

    def __init__(
        self,
        tenant_id: str = DEFAULT_TENANT_ID,
        session_id: str = "console-1",
        prompt: str = "You> ",
        bot_prefix: str = "Bot> ",
        actor: str = "human",
        **_: object,
    ) -> None:
        self.tenant_id = tenant_id
        self.session_id = session_id
        self.prompt = prompt
        self.bot_prefix = bot_prefix
        self.actor = SessionActor(actor)
        self._stop = False

    async def receive(self) -> AsyncIterator[InboundMessage]:
        loop = asyncio.get_event_loop()
        while not self._stop:
            try:
                line: Optional[str] = await loop.run_in_executor(
                    None, lambda: input(self.prompt)
                )
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if line is None:
                return
            text = line.strip()
            if not text:
                continue
            if text.lower() in {"exit", "quit", ":q"}:
                return
            yield InboundMessage(
                tenant_id=self.tenant_id,
                channel=self.name,
                session_id=self.session_id,
                text=text,
                actor=self.actor,
            )

    async def send(self, message: OutboundMessage) -> None:
        print(f"{self.bot_prefix}{message.text}")
        sys.stdout.flush()

    async def close(self) -> None:
        self._stop = True
