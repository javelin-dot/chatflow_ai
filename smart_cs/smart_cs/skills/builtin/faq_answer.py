"""faq_answer — return the best KB hit verbatim.

The simplest possible "knowledge → answer" skill. Replace with an LLM-backed
synthesizer once an LLM client is wired in.
"""
from __future__ import annotations

from ..skill import Skill, SkillContext, SkillRegistry, SkillResult


@SkillRegistry.register
class FAQAnswer(Skill):
    name = "faq_answer"
    description = "Return the best matching KB FAQ answer."

    def __init__(self, min_score: float = 0.4, **_: object) -> None:
        self.min_score = min_score

    async def run(self, ctx: SkillContext) -> SkillResult:
        if not ctx.hits:
            return SkillResult.empty()
        best = ctx.hits[0]
        if best.score < self.min_score:
            return SkillResult.empty()
        return SkillResult.reply(best.text, metadata={"kb_id": best.kb_id, "score": best.score})
