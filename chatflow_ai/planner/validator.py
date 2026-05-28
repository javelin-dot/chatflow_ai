# -*- coding: utf-8 -*-
"""
Static validation for LLM-generated Flow YAML.

Three things matter most:

1. **It parses** — without this, nothing downstream works.
2. **No invented operations** — every (service, operation_id) actually
   exists in the registry. This is the single biggest failure mode for
   LLM planners.
3. **Slot references resolve** — every `"slot:foo"` referenced in
   parameters / request_body has been previously set by an earlier
   collect / set_slot / response.slots in the same flow.

Issues are bucketed as `error` (block the write) vs `warning` (allow
but surface to the engineer). The CLI defaults to refusing to save the
file when there's an error; `--no-validate` skips this entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import yaml

from chatflow_ai.integrations import OpenAPIRegistry

# Match "slot:slot_name" mapping values, with optional whitespace around.
_SLOT_REF_RE = re.compile(r"^\s*slot:([A-Za-z_][\w]*)\s*$")
# Match "{slot_name}" placeholders in success/failure messages.
_TEMPLATE_RE = re.compile(r"\{([A-Za-z_][\w]*)\}")


@dataclass
class ValidationIssue:
    severity: str  # "error" or "warning"
    location: str  # e.g. "flows.onboard.steps[2]"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.location}: {self.message}"


@dataclass
class _SlotState:
    """Track which slots have been provided up to a given step within a flow."""

    provided: Set[str] = field(default_factory=set)

    def provide(self, name: str) -> None:
        self.provided.add(name)


def validate_flow_yaml(
    yaml_text: str,
    registry: OpenAPIRegistry,
) -> List[ValidationIssue]:
    """Return a list of issues; empty list means clean."""
    issues: List[ValidationIssue] = []

    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        issues.append(ValidationIssue("error", "<root>", f"YAML 解析失败：{e}"))
        return issues

    if not isinstance(parsed, dict) or "flows" not in parsed:
        issues.append(ValidationIssue("error", "<root>", "顶层缺少 `flows:` 键"))
        return issues

    flows = parsed.get("flows")
    if not isinstance(flows, dict) or not flows:
        issues.append(ValidationIssue("error", "flows", "`flows:` 必须是非空字典"))
        return issues

    for flow_id, flow in flows.items():
        loc = f"flows.{flow_id}"
        if not isinstance(flow, dict):
            issues.append(ValidationIssue("error", loc, "flow 必须是字典"))
            continue
        steps = flow.get("steps")
        if not isinstance(steps, list) or not steps:
            issues.append(ValidationIssue("error", loc, "`steps:` 必须是非空列表"))
            continue
        _validate_steps(loc, steps, registry, issues)

    return issues


def _validate_steps(
    flow_loc: str,
    steps: List[Any],
    registry: OpenAPIRegistry,
    issues: List[ValidationIssue],
) -> None:
    slot_state = _SlotState()
    step_ids: Set[str] = set()

    # First pass: collect all step ids so we can validate next references.
    for step in steps:
        if isinstance(step, dict) and step.get("id"):
            step_ids.add(str(step["id"]))

    for index, step in enumerate(steps):
        loc = f"{flow_loc}.steps[{index}]"
        if not isinstance(step, dict):
            issues.append(ValidationIssue("error", loc, "step 必须是字典"))
            continue
        if not step.get("id"):
            issues.append(ValidationIssue("error", loc, "step 缺少 `id`"))

        # Track which slots this step provides going forward.
        if "collect" in step:
            slot_state.provide(str(step["collect"]))
        if "set_slots" in step and isinstance(step["set_slots"], list):
            for entry in step["set_slots"]:
                if isinstance(entry, dict):
                    for name in entry.keys():
                        slot_state.provide(str(name))
        if "set_slot" in step and isinstance(step["set_slot"], dict):
            for name in step["set_slot"].keys():
                slot_state.provide(str(name))

        # OpenAPI action: validate service/operation_id + slot refs in
        # parameters / request_body; track response.slots as provided.
        if step.get("action") == "action_call_openapi":
            _validate_openapi_step(loc, step, registry, slot_state, issues)

        # next reference (allow "end" sentinel).
        nxt = step.get("next")
        if nxt is not None and nxt != "end" and str(nxt) not in step_ids:
            issues.append(
                ValidationIssue(
                    "warning",
                    loc,
                    f"`next: {nxt}` 在本 flow 的 step id 中找不到（可能是嵌套结构，请人工确认）",
                )
            )


def _validate_openapi_step(
    loc: str,
    step: Dict[str, Any],
    registry: OpenAPIRegistry,
    slot_state: _SlotState,
    issues: List[ValidationIssue],
) -> None:
    metadata = step.get("metadata") or {}
    openapi_cfg = metadata.get("openapi") if isinstance(metadata, dict) else None
    if not isinstance(openapi_cfg, dict):
        issues.append(
            ValidationIssue("error", loc, "action_call_openapi 缺少 `metadata.openapi` 配置")
        )
        return

    service = openapi_cfg.get("service")
    operation_id = openapi_cfg.get("operation_id")

    if not operation_id:
        issues.append(ValidationIssue("error", loc, "`metadata.openapi.operation_id` 必填"))
    if not service:
        issues.append(
            ValidationIssue("error", loc, "`metadata.openapi.service` 必填（规划器生成的 flow 应始终走 registry）")
        )

    entry = None
    if service and operation_id:
        try:
            _client, entry = registry.resolve(str(service), str(operation_id))
        except Exception as e:
            issues.append(
                ValidationIssue(
                    "error",
                    loc,
                    f"未注册的接口：service={service}, operation_id={operation_id}（{e}）",
                )
            )

    # Slot references in parameters and request_body.
    for section in ("parameters", "request_body", "headers"):
        section_cfg = openapi_cfg.get(section) or {}
        for issue in _walk_slot_refs(section_cfg, slot_state):
            issues.append(
                ValidationIssue(
                    "error",
                    f"{loc}.metadata.openapi.{section}",
                    issue,
                )
            )

    # Schema sanity: warn when a required body field is not wired up.
    if entry is not None and entry.request_body and isinstance(openapi_cfg.get("request_body"), dict):
        schema = entry.request_body.get("schema") or {}
        required = set(schema.get("required") or []) if isinstance(schema, dict) else set()
        wired = set(openapi_cfg["request_body"].keys())
        missing = required - wired
        if missing:
            issues.append(
                ValidationIssue(
                    "warning",
                    f"{loc}.metadata.openapi.request_body",
                    f"未提供 schema 中标记为 required 的字段：{sorted(missing)}",
                )
            )

    # response.slots provides new slots for later steps.
    response_cfg = openapi_cfg.get("response") or {}
    if isinstance(response_cfg, dict):
        rs = response_cfg.get("slots") or {}
        if isinstance(rs, dict):
            for name in rs.keys():
                slot_state.provide(str(name))
        for tmpl_key in ("success_message", "failure_message"):
            tmpl = response_cfg.get(tmpl_key)
            if isinstance(tmpl, str):
                for slot in _TEMPLATE_RE.findall(tmpl):
                    # status_code is always available; skip the well-known names.
                    if slot in {"status_code", "ok"}:
                        continue
                    if slot not in slot_state.provided:
                        issues.append(
                            ValidationIssue(
                                "warning",
                                f"{loc}.metadata.openapi.response.{tmpl_key}",
                                f"模板引用了未提供的槽位 `{{{slot}}}`",
                            )
                        )


def _walk_slot_refs(node: Any, slot_state: _SlotState) -> List[str]:
    """Walk a (possibly nested) parameters/body dict and check slot refs."""
    issues: List[str] = []
    if isinstance(node, dict):
        for v in node.values():
            issues.extend(_walk_slot_refs(v, slot_state))
    elif isinstance(node, list):
        for v in node:
            issues.extend(_walk_slot_refs(v, slot_state))
    elif isinstance(node, str):
        m = _SLOT_REF_RE.match(node)
        if m:
            name = m.group(1)
            if name not in slot_state.provided:
                issues.append(f"引用了未提供的槽位 `slot:{name}`")
    return issues


def format_issues(issues: List[ValidationIssue]) -> str:
    if not issues:
        return "(no issues)"
    return "\n".join(str(i) for i in issues)


def has_errors(issues: List[ValidationIssue]) -> bool:
    return any(i.severity == "error" for i in issues)
