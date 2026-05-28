# -*- coding: utf-8 -*-
"""
WorkflowPlanner — turn a natural-language business description into a
Flow YAML using the registered OpenAPI catalog.

Pipeline:

    description + services
        ↓
    registry.summarize_for_llm(services) → catalog text
        ↓
    LLM(system + user prompts)  → raw YAML text
        ↓
    strip_code_fence (defensive cleanup)
        ↓
    validate_flow_yaml          → issues
        ↓
    PlanResult(yaml_text, issues)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from chatflow_ai.integrations import OpenAPIRegistry
from chatflow_ai.planner.prompts import (
    build_planner_messages,
    strip_code_fence,
)
from chatflow_ai.planner.validator import (
    ValidationIssue,
    has_errors,
    validate_flow_yaml,
)
from chatflow_ai.shared.llm import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class PlanResult:
    """Outcome of a planning call.

    yaml_text is always populated (even if validation failed) so the
    engineer can see what the LLM produced and fix it by hand.
    """

    yaml_text: str
    issues: List[ValidationIssue] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: Optional[str] = None

    @property
    def has_errors(self) -> bool:
        return has_errors(self.issues)


class WorkflowPlanner:
    """Plans Flow YAML from a business description.

    The planner is stateless across calls — it holds references to the
    registry and an LLMClient and re-builds the prompt each time. Cheap
    to construct, safe to share across requests.
    """

    def __init__(self, registry: OpenAPIRegistry, llm_client: LLMClient) -> None:
        self.registry = registry
        self.llm_client = llm_client

    async def plan(
        self,
        description: str,
        services: Optional[List[str]] = None,
        validate: bool = True,
    ) -> PlanResult:
        if services:
            unknown = [s for s in services if s not in self.registry.services()]
            if unknown:
                raise ValueError(
                    f"未注册的服务：{unknown}（已注册：{self.registry.services()}）"
                )

        catalog = self.registry.summarize_for_llm(
            services=services,
            include_schemas=True,
        )
        if not catalog.strip():
            raise ValueError("注册表为空，无可用接口供规划")

        messages = build_planner_messages(description=description, catalog=catalog)

        logger.info(
            "Planning workflow (description=%r, services=%s, catalog_chars=%d)",
            description[:60],
            services or "all",
            len(catalog),
        )

        response = await self.llm_client.complete(messages)
        raw = response.content
        yaml_text = strip_code_fence(raw)

        issues: List[ValidationIssue] = []
        if validate:
            issues = validate_flow_yaml(yaml_text, self.registry)

        return PlanResult(
            yaml_text=yaml_text,
            issues=issues,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            raw_response=raw,
        )
