from __future__ import annotations

from datetime import datetime

import pytest

from chatflow_ai.workflow.models import (
    ExecutionContext,
    ParameterMapping,
    StepResult,
    WorkflowStep,
    WorkflowTemplate,
)


def test_parameter_mapping_const():
    """ParameterMapping with source='const' validates correctly."""
    pm = ParameterMapping(source="const", value="hello")
    assert pm.source == "const"
    assert pm.value == "hello"


def test_workflow_step_minimal():
    """WorkflowStep with minimal fields validates correctly."""
    step = WorkflowStep(id="step_1", name="Greet", operation_id="op.greet")
    assert step.id == "step_1"
    assert step.name == "Greet"
    assert step.operation_id == "op.greet"
    assert step.parameter_mapping == {}
    assert step.body_mapping is None
    assert step.save_response_to is None


def test_workflow_template_roundtrip():
    """Create a template with 2 steps, serialize and restore."""
    template = WorkflowTemplate(
        id="wf_1",
        name="Test Workflow",
        description="A test workflow",
        service_id="svc_test",
        steps=[
            WorkflowStep(
                id="step_1",
                name="First Step",
                operation_id="op.first",
                parameter_mapping={"name": ParameterMapping(source="const", value="Alice")},
                save_response_to="result_1",
            ),
            WorkflowStep(
                id="step_2",
                name="Second Step",
                operation_id="op.second",
                parameter_mapping={"ref": ParameterMapping(source="context", value="result_1")},
                body_mapping={"payload": ParameterMapping(source="prompt", value="summarize")},
            ),
        ],
    )

    # Serialize to JSON-serializable dict
    dumped = template.model_dump(mode="json")

    # Restore from dict
    restored = WorkflowTemplate.model_validate(dumped)

    # Assert equality
    assert restored.id == template.id
    assert restored.name == template.name
    assert restored.description == template.description
    assert restored.service_id == template.service_id
    assert len(restored.steps) == len(template.steps)

    for orig, back in zip(template.steps, restored.steps):
        assert back.id == orig.id
        assert back.name == orig.name
        assert back.operation_id == orig.operation_id
        assert back.parameter_mapping == orig.parameter_mapping
        assert back.body_mapping == orig.body_mapping
        assert back.save_response_to == orig.save_response_to

    # Also assert datetime fields survive roundtrip (as ISO strings in JSON mode)
    assert isinstance(restored.created_at, datetime)
    assert isinstance(restored.updated_at, datetime)


def test_step_result_defaults():
    """StepResult with only step_id uses correct defaults."""
    result = StepResult(step_id="step_1")
    assert result.step_id == "step_1"
    assert result.status == "pending"
    assert result.request == {}
    assert result.response == {}
    assert result.extracted == {}


def test_execution_context_defaults():
    """ExecutionContext with workflow_id and run_id uses correct defaults."""
    ctx = ExecutionContext(workflow_id="wf_1", run_id="run_1")
    assert ctx.workflow_id == "wf_1"
    assert ctx.run_id == "run_1"
    assert ctx.status == "running"
    assert ctx.step_results == {}
    assert ctx.variables == {}


def test_execution_context_with_results():
    """ExecutionContext stores provided step_results correctly."""
    result = StepResult(step_id="step_1", status="completed")
    ctx = ExecutionContext(
        workflow_id="wf_1",
        run_id="run_1",
        step_results={"step_1": result},
    )
    assert ctx.step_results == {"step_1": result}
    assert ctx.step_results["step_1"].status == "completed"
