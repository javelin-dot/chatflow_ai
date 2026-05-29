from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from chatflow_ai.integrations.openapi import get_path_value
from chatflow_ai.integrations.registry import OpenAPIRegistry
from chatflow_ai.workflow.models import (
    ExecutionContext,
    ParameterMapping,
    StepResult,
    WorkflowTemplate,
)
from chatflow_ai.workflow.session_token import SessionTokenManager


class WorkflowRunner:
    def __init__(
        self,
        registry: OpenAPIRegistry,
        token_manager: SessionTokenManager,
    ) -> None:
        self._registry = registry
        self._token_manager = token_manager

    async def run(self, template: WorkflowTemplate) -> ExecutionContext:
        """Execute a linear workflow step by step."""
        run_id = str(uuid.uuid4())
        variables: Dict[str, Any] = {}
        step_results: Dict[str, StepResult] = {}
        context_status = "running"

        for step in template.steps:
            step_result = StepResult(
                step_id=step.id,
                status="running",
                started_at=datetime.utcnow(),
            )
            step_results[step.id] = step_result

            # Resolve parameters
            parameters = self._resolve_mapping(step.parameter_mapping, variables)

            # Resolve body mapping (nested dict of ParameterMapping)
            request_body = None
            if step.body_mapping is not None:
                request_body = self._resolve_mapping(step.body_mapping, variables)

            # Get auth headers and cookies
            headers, cookies = self._token_manager.inject_auth({}, template.service_id)

            # Resolve client and call operation
            client, _ = self._registry.resolve(template.service_id, step.operation_id)

            # Record request details for debugging
            step_result.request = {
                "method": client.get_operation(step.operation_id).method,
                "base_url": client.base_url,
                "parameters": parameters,
                "body": request_body,
                "headers": headers,
                "cookies": cookies,
            }

            response = await client.call_operation(
                step.operation_id,
                parameters=parameters,
                request_body=request_body,
                headers=headers,
                cookies=cookies,
            )

            step_result.response = response
            step_result.finished_at = datetime.utcnow()

            # Save response to variables if configured
            if step.save_response_to is not None:
                variables[step.save_response_to] = response.get("body")

            if not response.get("ok", False):
                step_result.status = "failed"
                context_status = "failed"
                break

            step_result.status = "success"

        if context_status != "failed":
            context_status = "success"

        return ExecutionContext(
            workflow_id=template.id,
            run_id=run_id,
            status=context_status,
            step_results=step_results,
            variables=variables,
        )

    def _resolve_mapping(
        self,
        mapping: Dict[str, Any],
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve a mapping where values may be ParameterMapping or nested dicts."""
        resolved: Dict[str, Any] = {}
        for key, value in mapping.items():
            if isinstance(value, ParameterMapping):
                if value.source == "const":
                    resolved[key] = value.value
                elif value.source == "context":
                    resolved[key] = get_path_value(variables, value.value)
                elif value.source == "prompt":
                    resolved[key] = None
                else:
                    resolved[key] = None
            elif isinstance(value, dict):
                resolved[key] = self._resolve_mapping(value, variables)
            else:
                resolved[key] = value
        return resolved
