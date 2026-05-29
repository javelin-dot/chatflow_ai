# -*- coding: utf-8 -*-
"""Tests for SessionTokenManager."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

import pytest


class FakeClient:
    """Fake OpenAPIClient for testing."""

    def __init__(self, response: Optional[Dict[str, Any]] = None) -> None:
        self.calls: list = []
        self._response = response or {"data": {"token": "abc123"}}

    async def call_operation(
        self,
        operation_id: str,
        *,
        parameters: Optional[Mapping[str, Any]] = None,
        request_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        self.calls.append(
            {
                "operation_id": operation_id,
                "parameters": dict(parameters or {}),
                "request_body": dict(request_body or {}),
                "headers": dict(headers or {}),
            }
        )
        return self._response


class FakeRegistry:
    """Fake OpenAPIRegistry for testing."""

    def __init__(self, client: FakeClient) -> None:
        self._client = client

    def resolve(
        self, service_id: str, operation_id: str
    ) -> tuple[FakeClient, Any]:
        return self._client, None


@pytest.mark.asyncio
async def test_login_and_get_token() -> None:
    from chatflow_ai.workflow.session_token import SessionTokenManager

    manager = SessionTokenManager()
    fake_client = FakeClient()
    fake_registry = FakeRegistry(fake_client)

    token = await manager.login(
        registry=fake_registry,
        service_id="test_service",
        operation_id="login",
        credentials={"username": "user", "password": "pass"},
    )

    assert token == "Bearer abc123"
    assert await manager.get_token("test_service") == "Bearer abc123"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["operation_id"] == "login"
    assert fake_client.calls[0]["request_body"] == {
        "username": "user",
        "password": "pass",
    }


@pytest.mark.asyncio
async def test_inject_auth() -> None:
    from chatflow_ai.workflow.session_token import SessionTokenManager

    manager = SessionTokenManager()
    fake_client = FakeClient()
    fake_registry = FakeRegistry(fake_client)

    await manager.login(
        registry=fake_registry,
        service_id="test_service",
        operation_id="login",
        credentials={"username": "user", "password": "pass"},
    )

    headers = {"Content-Type": "application/json"}
    result = manager.inject_auth(headers, "test_service")

    assert result == {
        "Content-Type": "application/json",
        "Authorization": "Bearer abc123",
    }
    # Original headers should not be mutated
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_refresh() -> None:
    from chatflow_ai.workflow.session_token import SessionTokenManager

    manager = SessionTokenManager()
    fake_client = FakeClient()
    fake_registry = FakeRegistry(fake_client)

    await manager.login(
        registry=fake_registry,
        service_id="test_service",
        operation_id="login",
        credentials={"username": "user", "password": "pass"},
        token_path="data.token",
        token_prefix="Token ",
    )

    # Change response for refresh
    fake_client._response = {"data": {"token": "new_token"}}
    token = await manager.refresh(fake_registry, "test_service")

    assert token == "Token new_token"
    assert await manager.get_token("test_service") == "Token new_token"
    assert len(fake_client.calls) == 2
    assert fake_client.calls[1]["operation_id"] == "login"


@pytest.mark.asyncio
async def test_clear() -> None:
    from chatflow_ai.workflow.session_token import SessionTokenManager

    manager = SessionTokenManager()
    fake_client = FakeClient()
    fake_registry = FakeRegistry(fake_client)

    await manager.login(
        registry=fake_registry,
        service_id="svc1",
        operation_id="login",
        credentials={"username": "user1", "password": "pass1"},
    )
    await manager.login(
        registry=fake_registry,
        service_id="svc2",
        operation_id="login",
        credentials={"username": "user2", "password": "pass2"},
    )

    assert await manager.get_token("svc1") is not None
    assert await manager.get_token("svc2") is not None

    manager.clear("svc1")
    assert await manager.get_token("svc1") is None
    assert await manager.get_token("svc2") is not None

    manager.clear()
    assert await manager.get_token("svc2") is None


@pytest.mark.asyncio
async def test_inject_auth_no_token() -> None:
    from chatflow_ai.workflow.session_token import SessionTokenManager

    manager = SessionTokenManager()
    headers = {"Content-Type": "application/json"}
    result = manager.inject_auth(headers, "unknown_service")

    assert result == headers
    assert "Authorization" not in result
