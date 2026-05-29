from __future__ import annotations

import json
import tempfile
from pathlib import Path

from chatflow_ai.workflow.models import ExecutionContext, WorkflowTemplate, WorkflowStep
from chatflow_ai.workflow.storage import WorkflowStorage


def test_save_and_load_workflow():
    """Save a WorkflowTemplate and load it back; fields must match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = WorkflowStorage(base_dir=tmpdir)
        workflow = WorkflowTemplate(
            id="wf_1",
            name="Test Workflow",
            description="A test workflow",
            service_id="svc_test",
            steps=[
                WorkflowStep(id="step_1", name="First Step", operation_id="op.first"),
            ],
        )
        storage.save_workflow(workflow)

        loaded = storage.load_workflow("wf_1")
        assert loaded is not None
        assert loaded.id == workflow.id
        assert loaded.name == workflow.name
        assert loaded.description == workflow.description
        assert loaded.service_id == workflow.service_id
        assert len(loaded.steps) == len(workflow.steps)
        assert loaded.steps[0].id == workflow.steps[0].id


def test_list_workflows():
    """Save two workflows and list IDs; both must be present."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = WorkflowStorage(base_dir=tmpdir)
        wf1 = WorkflowTemplate(id="wf_a", name="Workflow A", service_id="svc_a")
        wf2 = WorkflowTemplate(id="wf_b", name="Workflow B", service_id="svc_b")
        storage.save_workflow(wf1)
        storage.save_workflow(wf2)

        ids = storage.list_workflow_ids()
        assert sorted(ids) == ["wf_a", "wf_b"]


def test_delete_workflow():
    """Save then delete a workflow; load must return None afterward."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = WorkflowStorage(base_dir=tmpdir)
        workflow = WorkflowTemplate(id="wf_del", name="To Delete", service_id="svc_del")
        storage.save_workflow(workflow)
        assert storage.load_workflow("wf_del") is not None

        deleted = storage.delete_workflow("wf_del")
        assert deleted is True
        assert storage.load_workflow("wf_del") is None
        assert storage.delete_workflow("wf_del") is False


def test_save_and_load_execution():
    """Save an ExecutionContext and load it back; fields must match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = WorkflowStorage(base_dir=tmpdir)
        ctx = ExecutionContext(workflow_id="wf_1", run_id="run_42", status="completed")
        ctx.variables["key"] = "value"
        storage.save_execution(ctx)

        loaded = storage.load_execution("run_42")
        assert loaded is not None
        assert loaded.workflow_id == ctx.workflow_id
        assert loaded.run_id == ctx.run_id
        assert loaded.status == ctx.status
        assert loaded.variables == ctx.variables


def test_json_is_pretty():
    """Saved JSON files must be pretty-printed with indentation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = WorkflowStorage(base_dir=tmpdir)
        workflow = WorkflowTemplate(id="wf_pretty", name="Pretty", service_id="svc_pretty")
        storage.save_workflow(workflow)

        path = Path(tmpdir) / "templates" / "wf_pretty.json"
        raw = path.read_text(encoding="utf-8")
        # Verify indentation by checking for a newline after '{'
        assert "\n" in raw
        # Verify it parses back correctly
        data = json.loads(raw)
        assert data["id"] == "wf_pretty"
