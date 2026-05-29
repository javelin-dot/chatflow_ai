from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from chatflow_ai.integrations.openapi import OpenAPICallError
from chatflow_ai.integrations.registry import (
    get_registry,
    service_spec_from_dict,
)
from chatflow_ai.workflow.models import ExecutionContext, WorkflowTemplate
from chatflow_ai.workflow.runner import WorkflowRunner
from chatflow_ai.workflow.session_token import SessionTokenManager
from chatflow_ai.workflow.storage import WorkflowStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

_storage = WorkflowStorage()
_token_mgr = SessionTokenManager()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterServiceRequest(BaseModel):
    name: str
    spec_url: str
    base_url: Optional[str] = None


class RegisterServiceResponse(BaseModel):
    name: str
    operations: int


class ServiceSummary(BaseModel):
    name: str
    operation_count: int
    base_url: Optional[str] = None


class OperationDetail(BaseModel):
    operation_id: str
    method: str
    path: str
    summary: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None


class WorkflowSummary(BaseModel):
    id: str
    name: str
    service_id: str


class RunWorkflowResponse(BaseModel):
    run_id: str
    status: str


class LoginRequest(BaseModel):
    service_id: str
    operation_id: str
    credentials: Dict[str, Any]
    token_path: Optional[str] = "data.token"
    token_prefix: Optional[str] = "Bearer "


class LoginResponse(BaseModel):
    token: str
    service_id: str


class SessionSummary(BaseModel):
    service_id: str
    operation_id: str


# ---------------------------------------------------------------------------
# Service management
# ---------------------------------------------------------------------------

@router.post("/services", response_model=RegisterServiceResponse)
async def register_service(body: RegisterServiceRequest) -> RegisterServiceResponse:
    """Register a Swagger/OpenAPI service by URL."""
    try:
        registry = get_registry()
        spec = service_spec_from_dict(
            body.name,
            {"spec": body.spec_url, "base_url": body.base_url},
        )
        catalog = await registry.register(spec)
        return RegisterServiceResponse(name=body.name, operations=len(catalog))
    except OpenAPICallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to register service")
        # Distinguish network errors from other failures for better UX
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
            raise HTTPException(
                status_code=502,
                detail=f"无法连接到指定的 Swagger URL ({body.spec_url})，请检查地址是否正确或网络是否可达。",
            ) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/services", response_model=List[ServiceSummary])
async def list_services() -> List[ServiceSummary]:
    """List all registered services."""
    registry = get_registry()
    services = registry.services()
    result: List[ServiceSummary] = []
    for name in services:
        try:
            catalog = registry.get_catalog(name)
            # base_url is not exposed by registry; omit for MVP
            result.append(
                ServiceSummary(name=name, operation_count=len(catalog), base_url=None)
            )
        except OpenAPICallError:
            continue
    return result


@router.get("/services/{service_id}/operations", response_model=List[OperationDetail])
async def list_operations(service_id: str) -> List[OperationDetail]:
    """List all operations for a registered service."""
    registry = get_registry()
    try:
        catalog = registry.get_catalog(service_id)
    except OpenAPICallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [
        OperationDetail(
            operation_id=entry.operation_id,
            method=entry.method,
            path=entry.path,
            summary=entry.summary,
            description=entry.description,
            tags=entry.tags,
            parameters=entry.parameters,
            request_body=entry.request_body,
        )
        for entry in catalog
    ]


@router.get("/services/{service_id}/operations/{operation_id}", response_model=OperationDetail)
async def get_operation(service_id: str, operation_id: str) -> OperationDetail:
    """Get detail for a single operation."""
    registry = get_registry()
    try:
        catalog = registry.get_catalog(service_id)
    except OpenAPICallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    for entry in catalog:
        if entry.operation_id == operation_id:
            return OperationDetail(
                operation_id=entry.operation_id,
                method=entry.method,
                path=entry.path,
                summary=entry.summary,
                description=entry.description,
                tags=entry.tags,
                parameters=entry.parameters,
                request_body=entry.request_body,
            )

    raise HTTPException(status_code=404, detail=f"Operation '{operation_id}' not found in service '{service_id}'")


@router.delete("/services/{service_id}")
async def unregister_service(service_id: str) -> Dict[str, str]:
    """Unregister a service (not implemented in MVP)."""
    raise HTTPException(status_code=501, detail="Unregister service is not implemented in MVP")


# ---------------------------------------------------------------------------
# Workflow management
# ---------------------------------------------------------------------------

@router.post("/workflows", response_model=WorkflowTemplate)
async def create_workflow(template: WorkflowTemplate) -> WorkflowTemplate:
    """Create or update a workflow template."""
    _storage.save_workflow(template)
    return template


@router.get("/workflows", response_model=List[WorkflowSummary])
async def list_workflows() -> List[WorkflowSummary]:
    """List all stored workflow templates."""
    ids = _storage.list_workflow_ids()
    workflows: List[WorkflowSummary] = []
    for wid in ids:
        wf = _storage.load_workflow(wid)
        if wf is not None:
            workflows.append(WorkflowSummary(id=wf.id, name=wf.name, service_id=wf.service_id))
    return workflows


@router.get("/workflows/{workflow_id}", response_model=WorkflowTemplate)
async def get_workflow(workflow_id: str) -> WorkflowTemplate:
    """Get a workflow template by ID."""
    wf = _storage.load_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf


@router.put("/workflows/{workflow_id}", response_model=WorkflowTemplate)
async def update_workflow(workflow_id: str, template: WorkflowTemplate) -> WorkflowTemplate:
    """Update a workflow template."""
    if template.id != workflow_id:
        raise HTTPException(status_code=400, detail="Workflow ID in path does not match body")
    _storage.save_workflow(template)
    return template


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, str]:
    """Delete a workflow template."""
    if not _storage.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return {"status": "deleted", "workflow_id": workflow_id}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

@router.post("/workflows/{workflow_id}/runs", response_model=RunWorkflowResponse)
async def run_workflow(workflow_id: str) -> RunWorkflowResponse:
    """Run a workflow and return the run ID."""
    wf = _storage.load_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    registry = get_registry()
    runner = WorkflowRunner(registry, _token_mgr)
    try:
        context = await runner.run(wf)
    except OpenAPICallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Workflow execution failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _storage.save_execution(context)
    return RunWorkflowResponse(run_id=context.run_id, status=context.status)


@router.get("/runs/{run_id}", response_model=ExecutionContext)
async def get_run(run_id: str) -> ExecutionContext:
    """Get the full execution context for a run."""
    context = _storage.load_execution(run_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return context


# ---------------------------------------------------------------------------
# Session / Auth
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=LoginResponse)
async def create_session(body: LoginRequest) -> LoginResponse:
    """Login to a test environment and store the token."""
    registry = get_registry()
    try:
        token = await _token_mgr.login(
            registry=registry,
            service_id=body.service_id,
            operation_id=body.operation_id,
            credentials=body.credentials,
            token_path=body.token_path or "data.token",
            token_prefix=body.token_prefix or "Bearer ",
        )
    except OpenAPICallError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LoginResponse(token=token, service_id=body.service_id)


@router.delete("/sessions")
async def clear_sessions(service_id: Optional[str] = None) -> Dict[str, str]:
    """Clear session token(s)."""
    _token_mgr.clear(service_id)
    return {"status": "cleared"}


@router.get("/sessions", response_model=List[SessionSummary])
async def list_sessions() -> List[SessionSummary]:
    """List active sessions (services with stored tokens)."""
    # SessionTokenManager stores configs keyed by service_id
    sessions: List[SessionSummary] = []
    for svc, cfg in _token_mgr._configs.items():
        sessions.append(SessionSummary(service_id=svc, operation_id=cfg.get("operation_id", "")))
    return sessions
