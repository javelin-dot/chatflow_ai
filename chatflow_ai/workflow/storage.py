from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from chatflow_ai.workflow.models import ExecutionContext, WorkflowTemplate


class WorkflowStorage:
    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = str(Path.home() / ".chatflow" / "workflows")
        self.base_dir = Path(base_dir)
        self.templates_dir = self.base_dir / "templates"
        self.history_dir = self.base_dir / "history"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def save_workflow(self, workflow: WorkflowTemplate) -> None:
        path = self.templates_dir / f"{workflow.id}.json"
        data = workflow.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_workflow(self, workflow_id: str) -> Optional[WorkflowTemplate]:
        path = self.templates_dir / f"{workflow_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return WorkflowTemplate.model_validate(data)

    def list_workflow_ids(self) -> List[str]:
        ids = []
        for path in self.templates_dir.glob("*.json"):
            ids.append(path.stem)
        return ids

    def delete_workflow(self, workflow_id: str) -> bool:
        path = self.templates_dir / f"{workflow_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def save_execution(self, context: ExecutionContext) -> None:
        path = self.history_dir / f"{context.run_id}.json"
        data = context.model_dump(mode="json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_execution(self, run_id: str) -> Optional[ExecutionContext]:
        path = self.history_dir / f"{run_id}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionContext.model_validate(data)
