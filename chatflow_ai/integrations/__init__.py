# -*- coding: utf-8 -*-
"""
Integration adapters for external systems.
"""

from chatflow_ai.integrations.openapi import (
    OpenAPIClient,
    OpenAPICallError,
    OperationCatalogEntry,
)
from chatflow_ai.integrations.registry import (
    OpenAPIRegistry,
    ServiceSpec,
    get_registry,
    reset_registry,
    service_spec_from_dict,
)

__all__ = [
    "OpenAPIClient",
    "OpenAPICallError",
    "OperationCatalogEntry",
    "OpenAPIRegistry",
    "ServiceSpec",
    "get_registry",
    "reset_registry",
    "service_spec_from_dict",
]
