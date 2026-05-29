from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ParameterMapping(BaseModel):
    source: str
    value: str


class WorkflowStep(BaseModel):
    id: str
    name: str
    operation_id: str
    parameter_mapping: Dict[str, ParameterMapping] = Field(default_factory=dict)
    body_mapping: Optional[Dict[str, ParameterMapping]] = None
    save_response_to: Optional[str] = None


class WorkflowTemplate(BaseModel):
    id: str
    name: str
    description: str = ""
    service_id: str
    steps: List[WorkflowStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StepResult(BaseModel):
    step_id: str
    status: str = "pending"
    request: Dict[str, Any] = Field(default_factory=dict)
    response: Dict[str, Any] = Field(default_factory=dict)
    extracted: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ExecutionContext(BaseModel):
    workflow_id: str
    run_id: str
    status: str = "running"
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
