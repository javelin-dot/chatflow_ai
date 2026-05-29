# -*- coding: utf-8 -*-
"""Declarative configuration for a registered OpenAPI service."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

from chatflow_ai.integrations.openapi import OpenAPICallError

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
        token_prefix=str(
            data.get("token_prefix")
            if data.get("token_prefix") is not None
            else "Bearer "
        ),
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
