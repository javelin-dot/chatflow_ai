from __future__ import annotations

from typing import Any, Dict, Tuple

import pytest

from chatflow_ai.workflow.models import (
    ExecutionContext,
    ParameterMapping,
    StepResult,
    WorkflowStep,
    WorkflowTemplate,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list = []

    async def call_operation(
        self,
        operation_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        request_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "operation_id": operation_id,
                "parameters": parameters,
                "request_body": request_body,
                "headers": headers,
            }
        )
        if operation_id == "login":
            return {
                "status_code": 200,
                "ok": True,
                "headers": {},
                "body": {"token": "secret123"},
            }
        return {
            "status_code": 200,
            "ok": True,
            "headers": {},
            "body": {"result": operation_id},
        }


class FakeRegistry:
    def __init__(self, client: FakeClient) -> None:
        self._client = client

    def resolve(self, service: str, operation_id: str) -> Tuple[FakeClient, None]:
        return self._client, None


class FakeTokenManager:
    def inject_auth(self, headers: dict[str, str], service_id: str) -> dict[str, str]:
        return dict(headers)


@pytest.mark.asyncio
async def test_run_linear_workflow() -> None:
    from chatflow_ai.workflow.runner import WorkflowRunner

    fake_client = FakeClient()
    registry = FakeRegistry(fake_client)
    token_manager = FakeTokenManager()
    runner = WorkflowRunner(registry, token_manager)

    template = WorkflowTemplate(
        id="wf-1",
        name="Test Workflow",
        service_id="test-service",
        steps=[
            WorkflowStep(
                id="step-1",
                name="First Step",
                operation_id="op1",
            ),
            WorkflowStep(
                id="step-2",
                name="Second Step",
                operation_id="op2",
            ),
        ],
    )

    ctx = await runner.run(template)

    assert isinstance(ctx, ExecutionContext)
    assert ctx.workflow_id == "wf-1"
    assert ctx.status == "success"
    assert len(ctx.step_results) == 2

    step1 = ctx.step_results["step-1"]
    assert step1.status == "success"
    assert step1.response["ok"] is True

    step2 = ctx.step_results["step-2"]
    assert step2.status == "success"
    assert step2.response["ok"] is True

    assert len(fake_client.calls) == 2
    assert fake_client.calls[0]["operation_id"] == "op1"
    assert fake_client.calls[1]["operation_id"] == "op2"


@pytest.mark.asyncio
async def test_context_variable_passing() -> None:
    from chatflow_ai.workflow.runner import WorkflowRunner

    fake_client = FakeClient()
    registry = FakeRegistry(fake_client)
    token_manager = FakeTokenManager()
    runner = WorkflowRunner(registry, token_manager)

    template = WorkflowTemplate(
        id="wf-2",
        name="Context Passing Workflow",
        service_id="test-service",
        steps=[
            WorkflowStep(
                id="step-1",
                name="Login",
                operation_id="login",
                save_response_to="auth",
            ),
            WorkflowStep(
                id="step-2",
                name="Use Token",
                operation_id="get_user",
                parameter_mapping={
                    "token": ParameterMapping(source="context", value="auth.token"),
                },
            ),
        ],
    )

    ctx = await runner.run(template)

    assert ctx.status == "success"
    assert len(fake_client.calls) == 2

    # Step 1 should have been called with no params
    assert fake_client.calls[0]["parameters"] == {}

    # Step 2 should have resolved the context variable
    assert fake_client.calls[1]["parameters"] == {"token": "secret123"}

    # Verify variable was stored
    assert ctx.variables["auth"]["token"] == "secret123"


class FakeClientWithAuth(FakeClient):
    async def call_operation(
        self,
        operation_id: str,
        *,
        parameters: dict[str, Any] | None = None,
        request_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "operation_id": operation_id,
                "parameters": parameters,
                "request_body": request_body,
                "headers": headers,
            }
        )
        if operation_id == "login":
            return {
                "status_code": 200,
                "ok": True,
                "headers": {},
                "body": {"token": "secret123"},
            }
        return {
            "status_code": 200,
            "ok": True,
            "headers": {},
            "body": {"result": operation_id},
        }


@pytest.mark.asyncio
async def test_context_variable_passing_with_realistic_client() -> None:
    from chatflow_ai.workflow.runner import WorkflowRunner

    fake_client = FakeClientWithAuth()
    registry = FakeRegistry(fake_client)
    token_manager = FakeTokenManager()
    runner = WorkflowRunner(registry, token_manager)

    template = WorkflowTemplate(
        id="wf-3",
        name="Context Passing Workflow",
        service_id="test-service",
        steps=[
            WorkflowStep(
                id="step-1",
                name="Login",
                operation_id="login",
                save_response_to="auth",
            ),
            WorkflowStep(
                id="step-2",
                name="Use Token",
                operation_id="get_user",
                parameter_mapping={
                    "token": ParameterMapping(source="context", value="auth.token"),
                },
            ),
        ],
    )

    ctx = await runner.run(template)

    assert ctx.status == "success"
    assert len(fake_client.calls) == 2

    # Step 1 should have been called with no params
    assert fake_client.calls[0]["parameters"] == {}

    # Step 2 should have resolved the context variable
    assert fake_client.calls[1]["parameters"] == {"token": "secret123"}

    # Verify variable was stored
    assert ctx.variables["auth"]["token"] == "secret123"
