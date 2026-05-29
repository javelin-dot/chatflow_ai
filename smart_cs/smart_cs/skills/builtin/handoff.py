"""handoff — escalate to a human agent.

Triggers when the user explicitly asks for a person, OR when an upstream policy
flags the conversation for handoff. The real queueing logic lives in
handoff.manager; this skill only emits the reply and the signal.
"""
from __future__ import annotations

from ..skill import Skill, SkillContext, SkillRegistry, SkillResult

_TRIGGERS = ["人工", "转人工", "客服", "找人", "real person", "agent"]


@SkillRegistry.register
class Handoff(Skill):
    name = "handoff"
    description = "Hand the conversation off to a human agent."
    triggers = _TRIGGERS

    async def run(self, ctx: SkillContext) -> SkillResult:
        return SkillResult(
            replies=["已为您转接到人工客服，请稍候。"],
            handoff=True,
            metadata={"reason": "user_requested"},
        )

    @classmethod
    def detects(cls, text: str) -> bool:
        t = (text or "").lower()
        return any(k in t for k in _TRIGGERS)
