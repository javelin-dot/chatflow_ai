# -*- coding: utf-8 -*-
"""
CLI for inspecting registered OpenAPI services.

Loads `endpoints.yml` and walks the swagger documents *without* booting
the full Agent — keeps these commands fast and dependency-light.

Commands:
  chatflow services                                 — list registered services
  chatflow operations [--service S] [--search Q]    — list operations
  chatflow show-operation <service> <operationId>   — detailed prompt block
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click

from chatflow_ai.integrations import (
    OpenAPICallError,
    OpenAPIRegistry,
    get_registry,
    reset_registry,
    service_spec_from_dict,
)
from chatflow_ai.shared.config import EndpointsConfig

logger = logging.getLogger(__name__)


async def _load_registry(endpoints_path: Path) -> OpenAPIRegistry:
    """Populate the global registry from endpoints.yml — best-effort.

    A failed service is logged and skipped so other services still load
    (matches the Agent.load() behaviour).
    """
    reset_registry()
    config = EndpointsConfig.load(endpoints_path)
    registry = get_registry()
    for name, raw in (config.services or {}).items():
        try:
            spec = service_spec_from_dict(name, raw)
        except OpenAPICallError as e:
            click.echo(f"  ! invalid config for service '{name}': {e}", err=True)
            continue
        try:
            await registry.register(spec)
        except Exception as e:
            click.echo(f"  ! failed to load service '{name}' from {spec.spec}: {e}", err=True)
    return registry


def _endpoints_path(project_path: str) -> Path:
    return Path(project_path) / "endpoints.yml"


@click.command(name="services")
@click.option(
    "--project-path", "-p",
    default=".",
    show_default=True,
    help="项目根目录（含 endpoints.yml）",
)
def services_command(project_path: str) -> None:
    """列出 endpoints.yml 中注册的 OpenAPI 服务。"""
    endpoints = _endpoints_path(project_path)
    if not endpoints.exists():
        click.echo(f"endpoints.yml not found at {endpoints}", err=True)
        raise click.exceptions.Exit(1)

    registry = asyncio.run(_load_registry(endpoints))
    services = registry.services()
    if not services:
        click.echo("(no services registered)")
        return

    click.echo(f"Loaded {len(services)} service(s) from {endpoints}:")
    for name in services:
        catalog = registry.get_catalog(name)
        client = registry.get_client(name)
        auth = "token" if "Authorization" in (client.default_headers or {}) else "no-auth"
        click.echo(f"  - {name}  ({len(catalog)} ops, {auth}, base_url={client.base_url})")


@click.command(name="operations")
@click.option(
    "--project-path", "-p",
    default=".",
    show_default=True,
    help="项目根目录（含 endpoints.yml）",
)
@click.option(
    "--service", "-s",
    default=None,
    help="只列出指定服务",
)
@click.option(
    "--search", "-q",
    default=None,
    help="按关键字（operationId / path / summary / description / tag）过滤",
)
@click.option(
    "--prompt",
    is_flag=True,
    default=False,
    help="输出 Planner LLM 用的完整摘要（含参数与请求体 schema）",
)
def operations_command(
    project_path: str,
    service: Optional[str],
    search: Optional[str],
    prompt: bool,
) -> None:
    """列出已注册服务的 OpenAPI operations。"""
    endpoints = _endpoints_path(project_path)
    if not endpoints.exists():
        click.echo(f"endpoints.yml not found at {endpoints}", err=True)
        raise click.exceptions.Exit(1)

    registry = asyncio.run(_load_registry(endpoints))

    if service and service not in registry.services():
        click.echo(
            f"service '{service}' is not registered. known: {registry.services()}",
            err=True,
        )
        raise click.exceptions.Exit(1)

    if prompt:
        out = registry.summarize_for_llm(
            services=[service] if service else None,
            include_schemas=True,
        )
        click.echo(out if out else "(no operations)")
        return

    if search:
        entries = registry.find_operations(search, service=service)
    else:
        entries = registry.list_operations(service=service)

    if not entries:
        click.echo("(no matching operations)")
        return

    current_service = None
    for entry in entries:
        if entry.service != current_service:
            current_service = entry.service
            click.echo(f"\n# {current_service}")
        click.echo(f"  {entry.to_summary_line()}")


@click.command(name="show-operation")
@click.argument("service", required=True)
@click.argument("operation_id", required=True)
@click.option(
    "--project-path", "-p",
    default=".",
    show_default=True,
    help="项目根目录（含 endpoints.yml）",
)
def show_operation_command(
    service: str,
    operation_id: str,
    project_path: str,
) -> None:
    """打印某个 operation 的详细 prompt block（参数、请求体 schema 等）。"""
    endpoints = _endpoints_path(project_path)
    if not endpoints.exists():
        click.echo(f"endpoints.yml not found at {endpoints}", err=True)
        raise click.exceptions.Exit(1)

    registry = asyncio.run(_load_registry(endpoints))

    try:
        _client, entry = registry.resolve(service, operation_id)
    except OpenAPICallError as e:
        click.echo(str(e), err=True)
        raise click.exceptions.Exit(1)

    click.echo(entry.to_prompt_block(include_schemas=True))


__all__ = [
    "services_command",
    "operations_command",
    "show_operation_command",
]
