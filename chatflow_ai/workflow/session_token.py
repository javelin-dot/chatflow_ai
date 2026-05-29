# -*- coding: utf-8 -*-
"""SessionTokenManager for per-service auth tokens in test environments."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from chatflow_ai.integrations.openapi import get_path_value


class SessionTokenManager:
    """Manages per-service auth tokens for test environments.

    Tokens are stored in memory (MVP). Multi-user deployments should
    switch to Redis or a shared cache later.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

    async def login(
        self,
        registry,
        service_id: str,
        operation_id: str,
        credentials: Dict[str, Any],
        token_path: str = "body.data.token",
        token_prefix: str = "Bearer ",
    ) -> str:
        """Call the login operation, extract and store token."""
        client, _ = registry.resolve(service_id, operation_id)
        response = await client.call_operation(
            operation_id,
            request_body=credentials,
        )
        raw_token = get_path_value(response, token_path)
        if raw_token is None:
            raise ValueError(
                f"Token not found at path '{token_path}' in response for service '{service_id}'"
            )
        token = f"{token_prefix}{raw_token}"
        self._tokens[service_id] = token
        self._configs[service_id] = {
            "operation_id": operation_id,
            "credentials": dict(credentials),
            "token_path": token_path,
            "token_prefix": token_prefix,
        }
        return token

    async def refresh(self, registry, service_id: str) -> str:
        """Re-run login using stored config."""
        config = self._configs.get(service_id)
        if config is None:
            raise ValueError(f"No stored login config for service '{service_id}'")
        return await self.login(
            registry=registry,
            service_id=service_id,
            operation_id=config["operation_id"],
            credentials=config["credentials"],
            token_path=config["token_path"],
            token_prefix=config["token_prefix"],
        )

    async def get_token(self, service_id: str) -> Optional[str]:
        """Get current valid token."""
        return self._tokens.get(service_id)

    def inject_auth(self, headers: Dict[str, str], service_id: str) -> Dict[str, str]:
        """Inject Authorization header if token exists."""
        result = dict(headers)
        token = self._tokens.get(service_id)
        if token is not None:
            result["Authorization"] = token
        return result

    def clear(self, service_id: Optional[str] = None) -> None:
        """Clear token(s)."""
        if service_id is not None:
            self._tokens.pop(service_id, None)
            self._configs.pop(service_id, None)
        else:
            self._tokens.clear()
            self._configs.clear()
