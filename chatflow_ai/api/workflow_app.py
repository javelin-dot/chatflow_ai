from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chatflow_ai.api.workflow_routes import router


def create_workflow_app() -> FastAPI:
    """Factory function that creates a standalone FastAPI app for the workflow builder."""
    app = FastAPI(
        title="ChatFlow Workflow Builder",
        description="Standalone API for workflow management, service registry, and execution",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


def main() -> None:
    import uvicorn

    app = create_workflow_app()
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")


if __name__ == "__main__":
    main()
