"""route — pick the next skill (and pull retrieval hits along the way)."""
from __future__ import annotations

from ...nlu.router import IntentRouter
from ..state import ProcessingState


class Route:
    def __init__(self, router: IntentRouter) -> None:
        self._router = router

    async def __call__(self, state: ProcessingState) -> ProcessingState:
        decision = self._router.route(state.inbound.text)
        state.route_skill = decision.skill
        state.hits = decision.hits
        state.intent = decision.intent
        state.intent_score = decision.score
        return state
