"""act — run the chosen skill and capture replies."""
from __future__ import annotations

from typing import Dict

from ...skills.skill import Skill, SkillContext
from ..state import ProcessingState


class Act:
    def __init__(self, skills: Dict[str, Skill]) -> None:
        self._skills = skills

    async def __call__(self, state: ProcessingState) -> ProcessingState:
        name = state.route_skill or "fallback"
        skill = self._skills.get(name) or self._skills.get("fallback")
        if skill is None:
            state.replies.append("(no skill available)")
            return state
        ctx = SkillContext(
            session=state.session,  # type: ignore[arg-type]
            user_text=state.inbound.text,
            hits=state.hits,
            intent=state.intent,
            intent_score=state.intent_score,
        )
        result = await skill.run(ctx)
        for r in result.replies:
            state.replies.append(r)
        for k, v in result.slot_updates.items():
            state.session.set_slot(k, v)  # type: ignore[union-attr]
        if result.handoff:
            state.handoff_requested = True
        if not state.replies:
            # Skill returned empty — fall back to a generic answer.
            fb = self._skills.get("fallback")
            if fb is not None:
                fb_result = await fb.run(ctx)
                state.replies.extend(fb_result.replies)
        return state
