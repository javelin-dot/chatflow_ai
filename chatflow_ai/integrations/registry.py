# -*- coding: utf-8 -*-
"""
OpenAPI service registry.

The registry holds one OpenAPIClient per registered service (a logical
name like "kyc" or "user") plus the parsed operation catalog for that
service. ActionCallOpenAPI looks operations up here; the workflow
planner uses the catalog to build LLM prompts.

Wired at Agent startup from `endpoints.yml`:

    services:
      kyc:
        spec: http://kyc.internal:8080/v3/api-docs
        base_url: http://kyc.internal:8080         # optional, default from spec
        token_env: KYC_SERVICE_TOKEN               # optional
        token_header: Authorization                # optional, default "Authorization"
        token_prefix: "Bearer "                    # optional, default "Bearer "
        timeout: 30                                # optional
        default_headers:                           # optional
          X-Tenant: t1
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from chatflow_ai.integrations.openapi import (
    OpenAPICallError,
    OpenAPIClient,
    OperationCatalogEntry,
)

logger = logging.getLogger(__name__)


@dataclass
class ServiceSpec:
    """Declarative configuration for a registered service."""

    name: str
    spec: str
    base_url: Optional[str] = None
    token_env: Optional[str] = None
    token_header: str = "Authorization"
    token_prefix: str = "Bearer "
    timeout: float = 30.0
    default_headers: Dict[str, str] = field(default_factory=dict)

    def resolved_headers(self) -> Dict[str, str]:
        """Merge default_headers with token from env, if any."""
        headers = dict(self.default_headers)
        if self.token_env:
            token = os.environ.get(self.token_env)
            if token:
                headers[self.token_header] = f"{self.token_prefix}{token}"
            else:
                logger.warning(
                    "Service '%s' declares token_env=%s but no value is set; "
                    "calls will go out unauthenticated.",
                    self.name,
                    self.token_env,
                )
        return headers


class OpenAPIRegistry:
    """In-memory registry of OpenAPI services and their operation catalogs."""

    def __init__(self) -> None:
        self._clients: Dict[str, OpenAPIClient] = {}
        self._catalogs: Dict[str, List[OperationCatalogEntry]] = {}
        self._specs: Dict[str, ServiceSpec] = {}

    async def register(self, spec: ServiceSpec) -> List[OperationCatalogEntry]:
        """Load the swagger document for a service and index its operations."""
        client = await OpenAPIClient.from_source(
            spec.spec,
            base_url=spec.base_url,
            timeout=spec.timeout,
            default_headers=spec.resolved_headers(),
        )
        catalog = client.extract_catalog(spec.name)
        self._clients[spec.name] = client
        self._catalogs[spec.name] = catalog
        self._specs[spec.name] = spec
        logger.info(
            "Registered OpenAPI service '%s' from %s (%d operations)",
            spec.name,
            spec.spec,
            len(catalog),
        )
        return catalog

    async def reload(self, service_name: str) -> List[OperationCatalogEntry]:
        """Re-fetch the swagger doc for a service."""
        if service_name not in self._specs:
            raise OpenAPICallError(f"Unknown service: {service_name}")
        return await self.register(self._specs[service_name])

    def services(self) -> List[str]:
        return list(self._clients.keys())

    def get_client(self, service: str) -> OpenAPIClient:
        client = self._clients.get(service)
        if client is None:
            raise OpenAPICallError(f"Unknown service: {service}")
        return client

    def get_spec(self, service: str) -> ServiceSpec:
        spec = self._specs.get(service)
        if spec is None:
            raise OpenAPICallError(f"Unknown service: {service}")
        return spec

    def get_catalog(self, service: str) -> List[OperationCatalogEntry]:
        if service not in self._catalogs:
            raise OpenAPICallError(f"Unknown service: {service}")
        return list(self._catalogs[service])

    def list_operations(
        self, service: Optional[str] = None
    ) -> List[OperationCatalogEntry]:
        if service is not None:
            return self.get_catalog(service)
        return [entry for entries in self._catalogs.values() for entry in entries]

    def find_operations(
        self, keyword: str, service: Optional[str] = None
    ) -> List[OperationCatalogEntry]:
        """Substring match across operation_id, path, summary, description, tags."""
        needle = keyword.lower()
        results: List[OperationCatalogEntry] = []
        for entry in self.list_operations(service):
            haystacks = [
                entry.operation_id,
                entry.path,
                entry.summary,
                entry.description,
                " ".join(entry.tags),
            ]
            if any(needle in (h or "").lower() for h in haystacks):
                results.append(entry)
        return results

    def resolve(self, service: str, operation_id: str) -> Tuple[OpenAPIClient, OperationCatalogEntry]:
        """Return (client, entry) for a (service, operationId) pair."""
        client = self.get_client(service)
        for entry in self._catalogs.get(service, ()):
            if entry.operation_id == operation_id:
                return client, entry
        raise OpenAPICallError(
            f"operationId '{operation_id}' not found in service '{service}'"
        )

    def summarize_for_llm(
        self,
        services: Optional[List[str]] = None,
        include_schemas: bool = True,
    ) -> str:
        """Render a planner-friendly catalog summary, grouped by service.

        services: limit to these services; None means all registered.
        include_schemas: include request_body field lists (more useful but
                         larger). Disable when bumping into token limits.
        """
        target = services or sorted(self._catalogs.keys())
        sections: List[str] = []
        for name in target:
            entries = self._catalogs.get(name)
            if not entries:
                continue
            header = f"# service: {name} ({len(entries)} operations)"
            blocks = [entry.to_prompt_block(include_schemas=include_schemas) for entry in entries]
            sections.append("\n\n".join([header, *blocks]))
        return "\n\n".join(sections)

    def resolve_anywhere(self, operation_id: str) -> Tuple[OpenAPIClient, OperationCatalogEntry]:
        """Find an operationId across all services (errors if ambiguous)."""
        matches: List[Tuple[OpenAPIClient, OperationCatalogEntry]] = []
        for service, entries in self._catalogs.items():
            for entry in entries:
                if entry.operation_id == operation_id:
                    matches.append((self._clients[service], entry))
        if not matches:
            raise OpenAPICallError(f"operationId not found in any service: {operation_id}")
        if len(matches) > 1:
            services = ", ".join(sorted({m[1].service for m in matches}))
            raise OpenAPICallError(
                f"operationId '{operation_id}' is ambiguous across services: {services}; "
                "qualify with service name"
            )
        return matches[0]


_GLOBAL_REGISTRY: Optional[OpenAPIRegistry] = None


def get_registry() -> OpenAPIRegistry:
    """Process-wide registry singleton.

    Single-instance is enough for the current product (one Agent per
    process). Multi-tenant deployments can swap this for an Agent-scoped
    instance later.
    """
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = OpenAPIRegistry()
    return _GLOBAL_REGISTRY


def reset_registry() -> None:
    """Test helper — drop the singleton."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = None


def service_spec_from_dict(name: str, data: Mapping[str, object]) -> ServiceSpec:
    """Parse one entry under endpoints.yml `services:`."""
    spec_url = data.get("spec")
    if not spec_url:
        raise OpenAPICallError(f"Service '{name}' is missing required 'spec' field")
    return ServiceSpec(
        name=name,
        spec=str(spec_url),
        base_url=_optional_str(data.get("base_url")),
        token_env=_optional_str(data.get("token_env")),
        token_header=str(data.get("token_header") or "Authorization"),
        token_prefix=str(data.get("token_prefix") if data.get("token_prefix") is not None else "Bearer "),
        timeout=float(data.get("timeout", 30.0)),
        default_headers={
            str(k): str(v) for k, v in (data.get("default_headers") or {}).items()
        },
    )


def _optional_str(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text if text else None
