"""FastAPI server — REST entry into the Orchestrator.

Optional: only imported when the `api` extra is installed (fastapi/uvicorn).
"""
from __future__ import annotations

from typing import Any, Dict

from ..runtime import Runtime
from ..shared.constants import HDR_TENANT_ID, HDR_USER_ID
from ..shared.types import InboundMessage, SessionActor


def create_app(runtime: Runtime):
    try:
        from fastapi import FastAPI, Header, HTTPException, Request
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is not installed. Install with `pip install fastapi uvicorn`."
        ) from exc

    app = FastAPI(title="smart_cs", version=runtime.settings.version)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat")
    async def chat(request: Request) -> Dict[str, Any]:
        body = await request.json()
        text = body.get("message", "")
        session_id = body.get("session_id") or "anon"
        if not text:
            raise HTTPException(status_code=400, detail="message is required")

        tenant_id = request.headers.get(HDR_TENANT_ID, runtime.settings.tenant.id)
        user_id = request.headers.get(HDR_USER_ID)
        actor = SessionActor(request.headers.get("X-Actor", "human"))

        inbound = InboundMessage(
            tenant_id=tenant_id,
            channel="http",
            session_id=session_id,
            text=text,
            user_id=user_id,
            actor=actor,
        )
        out = await runtime.orchestrator.handle(inbound)
        return {
            "session_id": session_id,
            "reply": out.text,
            "payload": out.payload,
        }

    return app
