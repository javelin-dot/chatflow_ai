# -*- coding: utf-8 -*-
"""SessionTokenManager for per-service auth tokens and cookies in test environments."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from chatflow_ai.integrations.openapi import get_path_value


class SessionTokenManager:
    """Manages per-service auth tokens and cookies for test environments.

    Tokens are stored in memory (MVP). Multi-user deployments should
    switch to Redis or a shared cache later.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}
        self._cookies: Dict[str, Dict[str, str]] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

    async def login(
        self,
        registry,
        service_id: str,
        operation_id: str,
        credentials: Dict[str, Any],
        token_path: Optional[str] = "data.token",
        token_prefix: Optional[str] = "Bearer ",
        target_service: Optional[str] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Call the login operation, extract and store token and/or cookies."""
        store_key = target_service or service_id
        client, _ = registry.resolve(service_id, operation_id)
        response = await client.call_operation(
            operation_id,
            request_body=credentials,
        )

        # Extract token from JSON body (if configured)
        token: Optional[str] = None
        if token_path:
            raw_token = get_path_value(response, token_path)
            if raw_token is not None:
                token = f"{token_prefix or ''}{raw_token}"
                self._tokens[store_key] = token

        # Extract cookies from response
        cookies = response.get("cookies") or {}
        if cookies:
            self._cookies[store_key] = dict(cookies)

        if token is None and not cookies:
            raise ValueError(
                f"Neither token (path '{token_path}') nor cookies found in response for service '{service_id}'"
            )

        self._configs[store_key] = {
            "service_id": service_id,
            "operation_id": operation_id,
            "credentials": dict(credentials),
            "token_path": token_path,
            "token_prefix": token_prefix,
            "target_service": target_service,
        }
        return token or "", self._cookies.get(store_key, {})

    async def refresh(self, registry, service_id: str) -> Tuple[str, Dict[str, str]]:
        """Re-run login using stored config."""
        config = self._configs.get(service_id)
        if config is None:
            raise ValueError(f"No stored login config for service '{service_id}'")
        return await self.login(
            registry=registry,
            service_id=config["service_id"],
            operation_id=config["operation_id"],
            credentials=config["credentials"],
            token_path=config.get("token_path"),
            token_prefix=config.get("token_prefix"),
            target_service=config.get("target_service"),
        )

    async def get_token(self, service_id: str) -> Optional[str]:
        """Get current valid token."""
        return self._tokens.get(service_id)

    async def get_cookies(self, service_id: str) -> Dict[str, str]:
        """Get current cookies."""
        return dict(self._cookies.get(service_id, {}))

    def inject_auth(
        self, headers: Dict[str, str], service_id: str
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Inject Authorization header and cookies if they exist."""
        result_headers = dict(headers)
        token = self._tokens.get(service_id)
        if token is not None:
            result_headers["Authorization"] = token
        cookies = dict(self._cookies.get(service_id, {}))
        return result_headers, cookies

    def clear(self, service_id: Optional[str] = None) -> None:
        """Clear token(s) and cookies."""
        if service_id is not None:
            self._tokens.pop(service_id, None)
            self._cookies.pop(service_id, None)
            self._configs.pop(service_id, None)
        else:
            self._tokens.clear()
            self._cookies.clear()
            self._configs.clear()
