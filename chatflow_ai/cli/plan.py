# -*- coding: utf-8 -*-
"""
`chatflow plan` — let the LLM draft a Flow YAML from a business description.

Workflow:
1. Load endpoints.yml; populate the OpenAPI registry (same as `chatflow services`).
2. Pick the LLM model from endpoints.yml (`--model NAME`, default "default" or first).
3. Call WorkflowPlanner.plan(description, services).
4. Validate; if errors and not --force, refuse to write the file but
   still print the YAML so the engineer can fix and retry.
5. Write to `--out`, or stdout when `--print` is set / no `--out` given.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import click

from chatflow_ai.cli.services_cli import _load_registry
from chatflow_ai.planner import WorkflowPlanner
from chatflow_ai.planner.validator import format_issues
from chatflow_ai.shared.config import EndpointsConfig, LLMConfig
from chatflow_ai.shared.llm import create_llm_client

logger = logging.getLogger(__name__)


def _pick_model(endpoints: EndpointsConfig, model_name: Optional[str]) -> tuple[str, LLMConfig]:
    """Resolve `--model` to a (name, LLMConfig) pair.

    Default precedence: explicit name → "default" → first defined model.
    """
    if not endpoints.models:
        raise click.exceptions.UsageError(
            "endpoints.yml 中没有定义任何 `models:`；规划器需要一个 LLM 模型。"
        )
    if model_name:
        cfg = endpoints.models.get(model_name)
        if cfg is None:
            raise click.exceptions.UsageError(
                f"模型 '{model_name}' 未在 endpoints.yml 的 models 中定义；"
                f"可选：{list(endpoints.models.keys())}"
            )
        return model_name, cfg
    if "default" in endpoints.models:
        return "default", endpoints.models["default"]
    first = next(iter(endpoints.models))
    return first, endpoints.models[first]


def _split_services(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [s.strip() for s in value.split(",") if s.strip()]


@click.command(name="plan")
@click.option(
    "--description", "-d",
    required=True,
    help="业务描述（自然语言一句话或一段话）",
)
@click.option(
    "--services", "-s",
    default=None,
    help="限定使用的服务，逗号分隔（默认：全部已注册的服务）",
)
@click.option(
    "--out", "-o",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="输出 Flow YAML 文件路径（不指定则打印到 stdout）",
)
@click.option(
    "--model",
    default=None,
    help="endpoints.yml `models:` 中的模型名（默认：default，否则第一个）",
)
@click.option(
    "--project-path", "-p",
    default=".",
    show_default=True,
    help="项目根目录（含 endpoints.yml）",
)
@click.option(
    "--no-validate",
    is_flag=True,
    default=False,
    help="跳过校验（operationId 存在性、slot 引用等），直接输出 LLM 原文",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="即使校验报错也写入文件",
)
@click.option(
    "--print", "print_only",
    is_flag=True,
    default=False,
    help="只打印，不写文件",
)
def plan_command(
    description: str,
    services: Optional[str],
    out: Optional[str],
    model: Optional[str],
    project_path: str,
    no_validate: bool,
    force: bool,
    print_only: bool,
) -> None:
    """让 LLM 根据业务描述规划出一份 Flow YAML。"""
    endpoints_path = Path(project_path) / "endpoints.yml"
    if not endpoints_path.exists():
        click.echo(f"endpoints.yml not found at {endpoints_path}", err=True)
        raise click.exceptions.Exit(1)

    # 1. Load registry from endpoints.yml.
    registry = asyncio.run(_load_registry(endpoints_path))
    if not registry.services():
        click.echo("(registry is empty — declare services in endpoints.yml first)", err=True)
        raise click.exceptions.Exit(1)

    # 2. Pick LLM model.
    endpoints = EndpointsConfig.load(endpoints_path)
    model_name, llm_config = _pick_model(endpoints, model)
    llm_client = create_llm_client(
        type=llm_config.type,
        model=llm_config.model,
        api_key=llm_config.api_key,
        api_base=llm_config.api_base,
        temperature=llm_config.temperature,
        max_tokens=max(llm_config.max_tokens, 2048),  # Flow YAML can be long
        timeout=llm_config.timeout,
        enable_thinking=llm_config.enable_thinking,
        **(llm_config.extra or {}),
    )

    # 3. Plan.
    service_list = _split_services(services)
    planner = WorkflowPlanner(registry=registry, llm_client=llm_client)

    click.echo(
        f"Planning with model '{model_name}' ({llm_config.type}/{llm_config.model})"
        f"{' on services ' + ','.join(service_list) if service_list else ''}...",
        err=True,
    )

    try:
        result = asyncio.run(
            planner.plan(
                description=description,
                services=service_list,
                validate=not no_validate,
            )
        )
    except Exception as e:
        click.echo(f"planning failed: {e}", err=True)
        raise click.exceptions.Exit(1)

    # 4. Report token usage and validation issues to stderr so YAML on
    #    stdout stays clean for `chatflow plan ... > flow.yml` pipelines.
    if result.prompt_tokens or result.completion_tokens:
        click.echo(
            f"tokens: prompt={result.prompt_tokens} completion={result.completion_tokens}",
            err=True,
        )
    if result.issues:
        click.echo("--- validation ---", err=True)
        click.echo(format_issues(result.issues), err=True)
        click.echo("------------------", err=True)

    # 5. Write or print.
    if print_only or not out:
        click.echo(result.yaml_text)

    if out and not print_only:
        if result.has_errors and not force:
            click.echo(
                "refused to write file due to validation errors; "
                "re-run with --force, --no-validate, or --print to inspect.",
                err=True,
            )
            raise click.exceptions.Exit(2)
        Path(out).write_text(result.yaml_text, encoding="utf-8")
        click.echo(f"wrote {out}", err=True)


__all__ = ["plan_command"]
