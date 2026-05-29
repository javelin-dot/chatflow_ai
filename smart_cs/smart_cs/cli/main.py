"""smart-cs CLI entry."""
from __future__ import annotations

import asyncio
from pathlib import Path

import click

from ..config.settings import Settings
from ..reception.gateway import ChannelGateway
from ..runtime import build


@click.group()
def cli() -> None:
    """smart_cs — universal intelligent customer service base."""


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True, dir_okay=False), help="Path to config.yml")
def shell(config: str) -> None:
    """Run an interactive console session against the configured orchestrator."""
    settings = Settings.load(Path(config))
    runtime = build(settings)
    click.echo(
        f"[smart_cs] tenant={settings.tenant.id} workspace={settings.tenant.workspace} "
        f"channels={[c.name for c in runtime.channels]}"
    )
    click.echo("Type 'exit' or Ctrl-D to quit.\n")

    gateway = ChannelGateway(runtime.orchestrator.handle)
    if not runtime.channels:
        raise click.ClickException("no channels configured")

    async def _drive() -> None:
        # Pick the first console channel; complain if there is none.
        console_channels = [c for c in runtime.channels if c.name == "console"]
        if not console_channels:
            raise click.ClickException(
                "shell requires a 'console' channel in config; "
                "use `smart-cs run` for non-console channels."
            )
        await gateway.serve_one(console_channels[0])

    try:
        asyncio.run(_drive())
    except KeyboardInterrupt:
        pass


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8080, type=int)
def run(config: str, host: str, port: int) -> None:
    """Start the FastAPI HTTP server."""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise click.ClickException(
            "uvicorn not installed. Run `pip install uvicorn fastapi`."
        ) from exc

    settings = Settings.load(Path(config))
    runtime = build(settings)
    from ..api.server import create_app

    app = create_app(runtime)
    uvicorn.run(app, host=host, port=port)


@cli.command(name="init")
@click.argument("path", type=click.Path())
def init_cmd(path: str) -> None:
    """Scaffold a new smart_cs project at PATH."""
    target = Path(path)
    if target.exists() and any(target.iterdir()):
        raise click.ClickException(f"{path} exists and is not empty")
    target.mkdir(parents=True, exist_ok=True)
    (target / "kb").mkdir(exist_ok=True)
    (target / "config.yml").write_text(_DEFAULT_CONFIG, encoding="utf-8")
    (target / "kb" / "faq.yml").write_text(_DEFAULT_FAQ, encoding="utf-8")
    click.echo(f"Scaffolded smart_cs project at {target}")


_DEFAULT_CONFIG = """\
version: "0.1"

tenant:
  id: demo
  name: Demo Company
  workspace: default

reception:
  channels:
    - type: console

knowledge:
  bases:
    - id: faq_main
      type: faq_yaml
      source: ./kb/faq.yml

skills:
  enabled:
    - faq_answer
    - handoff

policies:
  - type: kb_policy
    priority: 50
  - type: handoff_policy
    priority: 30
  - type: fallback_policy
    priority: 10

governance:
  guardrail:
    enabled: true
    block_patterns: []
  audit:
    enabled: true
    sink: stdout
  quota:
    session_max_turns: 50
"""

_DEFAULT_FAQ = """\
- id: hello
  question: 你好
  keywords: [你好, hi, hello]
  answer: 您好！我是智能客服，请问有什么可以帮您？
"""


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
