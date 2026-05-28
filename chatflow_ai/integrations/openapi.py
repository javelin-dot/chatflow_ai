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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
from urllib.parse import quote

import httpx
import yaml


class OpenAPICallError(Exception):
    """Raised when an OpenAPI operation cannot be resolved or called."""


@dataclass
class OpenAPIOperation:
    """Resolved OpenAPI operation metadata."""

    operation_id: str
    method: str
    path: str
    definition: Dict[str, Any]


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

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                operation.method,
                url,
                params=parameters or None,
                json=request_body or None,
                headers=request_headers,
            )

        parsed_body: Any
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            parsed_body = response.json()
        else:
            parsed_body = response.text

        return {
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 300,
            "headers": dict(response.headers),
            "body": parsed_body,
        }

    def _base_url_from_spec(self) -> Optional[str]:
        servers = self.spec.get("servers") or []
        if servers and isinstance(servers[0], Mapping):
            url = servers[0].get("url")
            return str(url) if url else None
        return None


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
