"""ToolGuard — VCC-inspired tool access control for Agents.

Borrowed from WorldFirst's Virtual Credit Card (VCC) design pattern for AI
Agent payments. Core idea: never hand an Agent the master credentials. Issue
a scoped, expiring credential with:
  - whitelist of allowed tools (analog: allowed merchants)
  - quota: max calls / max tokens / max spend (analog: monthly cap)
  - expiry (analog: card valid_until; auto-revoke when session ends)
  - requires_confirmation for write/sensitive ops (analog: 3DS step-up)
  - full audit (analog: card statement)

Every Agent-initiated tool call goes through ToolGuard.invoke().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from ...shared.exceptions import ToolGuardError
from ...shared.types import new_id, utcnow
from .registry import ToolRegistry
from .tool import ToolInvocation


@dataclass
class ToolQuota:
    max_calls: Optional[int] = None
    max_tokens: Optional[int] = None  # placeholder for future LLM token accounting
    used_calls: int = 0
    used_tokens: int = 0

    def consume(self, calls: int = 1, tokens: int = 0) -> None:
        if self.max_calls is not None and self.used_calls + calls > self.max_calls:
            raise ToolGuardError(
                f"quota exceeded: max_calls={self.max_calls} used={self.used_calls}"
            )
        if self.max_tokens is not None and self.used_tokens + tokens > self.max_tokens:
            raise ToolGuardError(
                f"quota exceeded: max_tokens={self.max_tokens} used={self.used_tokens}"
            )
        self.used_calls += calls
        self.used_tokens += tokens


@dataclass
class ToolCredential:
    """One issued credential — analogous to one VCC card."""

    id: str
    actor: str  # "agent:<id>" or "human:<uid>"
    allowed_tools: List[str] = field(default_factory=list)
    quota: ToolQuota = field(default_factory=ToolQuota)
    requires_confirmation: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    revoked: bool = False
    issued_at: datetime = field(default_factory=utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and utcnow() >= self.expires_at:
            return False
        return True

    def is_allowed(self, tool_name: str) -> bool:
        return not self.allowed_tools or tool_name in self.allowed_tools

    def needs_confirmation(self, tool_name: str) -> bool:
        return tool_name in self.requires_confirmation


@dataclass
class ToolCallAudit:
    invocation: ToolInvocation
    credential_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    ok: bool = False
    error: Optional[str] = None
    result_summary: Optional[str] = None


AuditSink = Callable[[ToolCallAudit], None]


class ToolGuard:
    """Issues credentials and intercepts every tool call."""

    def __init__(
        self,
        registry: ToolRegistry,
        audit_sink: Optional[AuditSink] = None,
    ) -> None:
        self._registry = registry
        self._credentials: Dict[str, ToolCredential] = {}
        self._audit_sink: AuditSink = audit_sink or (lambda _: None)

    def issue(
        self,
        actor: str,
        *,
        allowed_tools: Optional[List[str]] = None,
        max_calls: Optional[int] = None,
        max_tokens: Optional[int] = None,
        requires_confirmation: Optional[List[str]] = None,
        ttl: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolCredential:
        """Issue a fresh scoped credential. Analog: open a new VCC card."""
        cred = ToolCredential(
            id=new_id("cred"),
            actor=actor,
            allowed_tools=allowed_tools or [],
            quota=ToolQuota(max_calls=max_calls, max_tokens=max_tokens),
            requires_confirmation=requires_confirmation or [],
            expires_at=utcnow() + ttl if ttl else None,
            metadata=metadata or {},
        )
        self._credentials[cred.id] = cred
        return cred

    def revoke(self, credential_id: str) -> None:
        """Cancel a credential. Analog: terminate the VCC card."""
        cred = self._credentials.get(credential_id)
        if cred:
            cred.revoked = True

    def credential(self, credential_id: str) -> ToolCredential:
        cred = self._credentials.get(credential_id)
        if cred is None:
            raise ToolGuardError(f"unknown credential: {credential_id}")
        return cred

    async def invoke(
        self,
        credential_id: str,
        invocation: ToolInvocation,
        *,
        confirmed: bool = False,
    ) -> Any:
        """Run a tool call under guard."""
        cred = self.credential(credential_id)
        if not cred.is_active():
            raise ToolGuardError(f"credential {cred.id} inactive (revoked or expired)")
        if not cred.is_allowed(invocation.tool):
            raise ToolGuardError(
                f"tool '{invocation.tool}' not in whitelist for credential {cred.id}"
            )
        if cred.needs_confirmation(invocation.tool) and not confirmed:
            raise ToolGuardError(
                f"tool '{invocation.tool}' requires explicit confirmation"
            )
        if not self._registry.has(invocation.tool):
            raise ToolGuardError(f"tool '{invocation.tool}' not registered")

        cred.quota.consume(calls=1)

        audit = ToolCallAudit(
            invocation=invocation,
            credential_id=cred.id,
            started_at=utcnow(),
        )
        try:
            tool = self._registry.get(invocation.tool)
            result = await tool.call(**invocation.arguments)
            audit.ok = True
            audit.result_summary = type(result).__name__
            return result
        except Exception as exc:  # noqa: BLE001
            audit.ok = False
            audit.error = repr(exc)
            raise
        finally:
            audit.finished_at = utcnow()
            self._audit_sink(audit)
