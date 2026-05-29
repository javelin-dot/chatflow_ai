"""Request-scoped tenant context using contextvars."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Iterator, Optional

from ..shared.constants import DEFAULT_TENANT_ID, DEFAULT_WORKSPACE_ID


@dataclass
class TenantContext:
    tenant_id: str = DEFAULT_TENANT_ID
    workspace_id: str = DEFAULT_WORKSPACE_ID
    user_id: Optional[str] = None


_current: ContextVar[Optional[TenantContext]] = ContextVar(
    "smart_cs_tenant_ctx", default=None
)


def current() -> TenantContext:
    """Return current tenant context, defaulting to the default tenant."""
    ctx = _current.get()
    if ctx is None:
        return TenantContext()
    return ctx


@contextmanager
def use(ctx: TenantContext) -> Iterator[TenantContext]:
    token = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)
