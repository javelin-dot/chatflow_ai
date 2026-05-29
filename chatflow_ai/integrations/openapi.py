# -*- coding: utf-8 -*-
"""
OpenAPI 3.x integration client.

This adapter intentionally implements a small runtime subset:
- load an OpenAPI JSON/YAML document from a local path or HTTP(S) URL
- resolve an operation by operationId
- map path/query/header parameters and JSON request body
- call the target service with httpx

It does not try to generate a typed SDK. ChatFlow flows stay in control of
which operation is callable and how slots map into request data.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import quote

import httpx
import yaml

logger = logging.getLogger(__name__)


class OpenAPICallError(Exception):
    """Raised when an OpenAPI operation cannot be resolved or called."""


@dataclass
class OpenAPIOperation:
    """Resolved OpenAPI operation metadata."""

    operation_id: str
    method: str
    path: str
    definition: Dict[str, Any]


@dataclass
class OperationCatalogEntry:
    """Catalog entry for an OpenAPI operation, used by Registry/Planner.

    Carries enough structural info to (1) prompt an LLM about what the
    operation does, and (2) drive ActionCallOpenAPI at runtime.
    """

    service: str
    operation_id: str
    method: str
    path: str
    summary: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)

    def required_parameters(self) -> List[str]:
        return [p["name"] for p in self.parameters if p.get("required")]

    def to_summary_line(self) -> str:
        """One-line summary for LLM prompts: METHOD path :: id — summary."""
        head = f"{self.method:6s} {self.path} :: {self.operation_id}"
        if self.summary:
            head = f"{head} — {self.summary}"
        return head

    def to_prompt_block(self, include_schemas: bool = True) -> str:
        """Multi-line block fed to the Planner LLM.

        Designed to be token-economical: only fields a planner needs to pick
        the operation and wire slots into it. Response schema is omitted by
        default (planner doesn't need it to compose calls); enable
        include_schemas for the full picture.
        """
        lines = [self.to_summary_line()]
        if self.tags:
            lines.append(f"  tags: {', '.join(self.tags)}")
        if self.description and self.description != self.summary:
            # Collapse multi-line descriptions to a single line to stay compact.
            desc = " ".join(self.description.split())
            if len(desc) > 200:
                desc = desc[:197] + "..."
            lines.append(f"  desc: {desc}")
        if self.parameters:
            lines.append("  params:")
            for param in self.parameters:
                req = "*" if param.get("required") else " "
                ptype = param.get("type") or "any"
                pdesc = (param.get("description") or "").strip()
                tail = f" — {pdesc}" if pdesc else ""
                lines.append(
                    f"    {req} {param['name']} ({param['in']}, {ptype}){tail}"
                )
        if self.request_body:
            req_mark = "*" if self.request_body.get("required") else " "
            lines.append(f"  body:{req_mark}")
            schema = self.request_body.get("schema")
            if include_schemas and isinstance(schema, Mapping):
                lines.append(_indent_schema(schema, indent="    "))
        return "\n".join(lines)


def _indent_schema(schema: Mapping[str, Any], indent: str = "") -> str:
    """Compact one-level rendering of a JSON-schema object for prompts.

    Goal: show field names + types + required without dumping the full
    nested schema (cheap, deterministic, good enough for the planner).
    """
    stype = schema.get("type")
    if stype == "object":
        required = set(schema.get("required") or [])
        props = schema.get("properties") or {}
        lines = []
        for name, prop in props.items():
            mark = "*" if name in required else " "
            ptype = prop.get("type") if isinstance(prop, Mapping) else "any"
            pdesc = ""
            if isinstance(prop, Mapping):
                pdesc = (prop.get("description") or "").strip()
            tail = f" — {pdesc}" if pdesc else ""
            lines.append(f"{indent}{mark} {name}: {ptype}{tail}")
        return "\n".join(lines) if lines else f"{indent}(empty object)"
    if stype == "array":
        item = schema.get("items") or {}
        item_type = item.get("type") if isinstance(item, Mapping) else "any"
        return f"{indent}array<{item_type}>"
    if stype:
        return f"{indent}{stype}"
    # Fall back to a $ref or untyped schema
    if isinstance(schema, Mapping) and "$ref" in schema:
        return f"{indent}{schema['$ref']}"
    return f"{indent}(schema omitted)"


class OpenAPIClient:
    """Small OpenAPI 3.x operation caller."""

    HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}

    def __init__(
        self,
        spec: Mapping[str, Any],
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.spec = dict(spec)
        self.base_url = (base_url or self._base_url_from_spec() or "").rstrip("/")
        self.timeout = timeout
        self.default_headers = dict(default_headers or {})

    @classmethod
    async def from_source(
        cls,
        source: str,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> "OpenAPIClient":
        """Load an OpenAPI document from a local path or HTTP(S) URL."""
        if source.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(source)
                response.raise_for_status()
                content = response.text
        else:
            content = Path(source).read_text(encoding="utf-8")

        spec = yaml.safe_load(content) or {}
        return cls(
            spec=spec,
            base_url=base_url,
            timeout=timeout,
            default_headers=default_headers,
        )

    def get_operation(self, operation_id: str) -> OpenAPIOperation:
        """Find an operation by operationId."""
        for path, path_item in (self.spec.get("paths") or {}).items():
            if not isinstance(path_item, Mapping):
                continue
            for method, operation in path_item.items():
                if method.lower() not in self.HTTP_METHODS:
                    continue
                if isinstance(operation, Mapping) and operation.get("operationId") == operation_id:
                    return OpenAPIOperation(
                        operation_id=operation_id,
                        method=method.upper(),
                        path=path,
                        definition=dict(operation),
                    )
        raise OpenAPICallError(f"OpenAPI operationId not found: {operation_id}")

    async def call_operation(
        self,
        operation_id: str,
        *,
        parameters: Optional[Mapping[str, Any]] = None,
        request_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        cookies: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call an operation and return response metadata plus parsed body."""
        if not self.base_url:
            raise OpenAPICallError("OpenAPI base_url is required")

        operation = self.get_operation(operation_id)
        parameters = dict(parameters or {})
        request_body = dict(request_body or {})
        request_headers = {
            "Accept": "application/json",
            **self.default_headers,
            **dict(headers or {}),
        }

        url_path = operation.path
        path_params = set(re.findall(r"{([^}]+)}", url_path))
        for name in path_params:
            if name not in parameters:
                raise OpenAPICallError(f"Missing path parameter: {name}")
            value = quote(str(parameters.pop(name)), safe="")
            url_path = url_path.replace("{" + name + "}", value)

        url = f"{self.base_url}{url_path}"
        logger.info(
            "OpenAPI call %s %s (params=%s, body=%s, cookies=%s)",
            operation.method,
            url,
            parameters,
            request_body,
            cookies,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                operation.method,
                url,
                params=parameters or None,
                json=request_body or None,
                headers=request_headers,
                cookies=dict(cookies) if cookies else None,
            )

        parsed_body: Any
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            parsed_body = response.json()
        else:
            parsed_body = response.text

        # Extract cookies from Set-Cookie headers
        response_cookies: Dict[str, str] = {}
        for cookie in response.cookies.jar:
            response_cookies[cookie.name] = cookie.value

        return {
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 300,
            "headers": dict(response.headers),
            "body": parsed_body,
            "url": url,
            "method": operation.method,
            "cookies": response_cookies,
        }

    def _base_url_from_spec(self) -> Optional[str]:
        servers = self.spec.get("servers") or []
        if servers and isinstance(servers[0], Mapping):
            url = servers[0].get("url")
            return str(url) if url else None
        return None

    def extract_catalog(self, service: str) -> List[OperationCatalogEntry]:
        """Walk the spec and produce one entry per operation.

        operationId is required (entries without it are skipped) so the
        Registry / Planner can address operations by stable id rather than
        method+path strings.
        """
        entries: List[OperationCatalogEntry] = []
        paths = self.spec.get("paths") or {}
        if not isinstance(paths, Mapping):
            return entries

        for path, path_item in paths.items():
            if not isinstance(path_item, Mapping):
                continue
            path_level_params = path_item.get("parameters") or []
            for method, operation in path_item.items():
                if method.lower() not in self.HTTP_METHODS:
                    continue
                if not isinstance(operation, Mapping):
                    continue
                operation_id = operation.get("operationId")
                if not operation_id:
                    continue

                merged_params: List[Dict[str, Any]] = []
                seen_keys = set()
                for raw in list(path_level_params) + list(operation.get("parameters") or []):
                    if not isinstance(raw, Mapping):
                        continue
                    name = raw.get("name")
                    location = raw.get("in")
                    if not name or not location:
                        continue
                    key = (name, location)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    schema = raw.get("schema") or {}
                    merged_params.append(
                        {
                            "name": name,
                            "in": location,
                            "required": bool(raw.get("required", location == "path")),
                            "type": schema.get("type"),
                            "description": raw.get("description", ""),
                        }
                    )

                request_body = None
                rb = operation.get("requestBody")
                if isinstance(rb, Mapping):
                    content = rb.get("content") or {}
                    json_media = content.get("application/json") if isinstance(content, Mapping) else None
                    request_body = {
                        "required": bool(rb.get("required", False)),
                        "schema": (json_media or {}).get("schema") if isinstance(json_media, Mapping) else None,
                    }

                tags = operation.get("tags") or []
                if not isinstance(tags, list):
                    tags = []

                entries.append(
                    OperationCatalogEntry(
                        service=service,
                        operation_id=operation_id,
                        method=method.upper(),
                        path=path,
                        summary=str(operation.get("summary") or ""),
                        description=str(operation.get("description") or ""),
                        tags=[str(t) for t in tags],
                        parameters=merged_params,
                        request_body=request_body,
                        responses=dict(operation.get("responses") or {}),
                    )
                )
        return entries


def get_path_value(data: Any, path: str) -> Any:
    """Read a dotted path from dict/list data, e.g. body.data.id."""
    current = data
    for part in path.split("."):
        if part == "":
            continue
        if isinstance(current, Mapping):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def render_template(value: Any, variables: Mapping[str, Any]) -> Any:
    """Render simple {name} placeholders in strings."""
    if not isinstance(value, str):
        return value
    rendered = value
    for key, item in variables.items():
        rendered = rendered.replace("{" + key + "}", "" if item is None else str(item))
    return rendered


def coerce_value(value: Any, variables: Mapping[str, Any]) -> Any:
    """Resolve mapping values like slot:user_name, const:x, or templates."""
    if not isinstance(value, str):
        return value
    if value.startswith("slot:"):
        return variables.get(value[5:])
    if value.startswith("const:"):
        return value[6:]
    return render_template(value, variables)


def resolve_mapping(mapping: Mapping[str, Any], variables: Mapping[str, Any]) -> Dict[str, Any]:
    """Resolve a nested mapping with slot/template values."""
    resolved: Dict[str, Any] = {}
    for key, value in mapping.items():
        if isinstance(value, Mapping):
            resolved[key] = resolve_mapping(value, variables)
        elif isinstance(value, list):
            resolved[key] = [
                resolve_mapping(item, variables) if isinstance(item, Mapping)
                else coerce_value(item, variables)
                for item in value
            ]
        else:
            resolved[key] = coerce_value(value, variables)
    return resolved
