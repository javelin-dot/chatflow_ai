"""fallback — the safety net reply when nothing else matched."""
from __future__ import annotations

from ..skill import Skill, SkillContext, SkillRegistry, SkillResult


@SkillRegistry.register
class Fallback(Skill):
    name = "fallback"
    description = "Generic fallback when no other skill handles the input."

    def __init__(self, message: str = "抱歉，我暂时没理解您的问题，可以换个说法或输入「人工」转接客服。", **_: object) -> None:
        self.message = message

    async def run(self, ctx: SkillContext) -> SkillResult:
        return SkillResult.reply(self.message)
