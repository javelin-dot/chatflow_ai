"""Runtime — wire a Settings into a ready-to-use Orchestrator and channels.

This module is the single place where dependency wiring lives. Keep it boring
so the rest of the code can stay declarative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

# Side-effect imports: register builtin channels / KBs / skills.
from .reception.channels import console as _channels_console  # noqa: F401
from .knowledge.store import memory as _kb_memory  # noqa: F401
from .skills.builtin import faq_answer as _skill_faq  # noqa: F401
from .skills.builtin import handoff as _skill_handoff  # noqa: F401
from .skills.builtin import fallback as _skill_fallback  # noqa: F401

from .config.settings import Settings
from .governance.audit import AuditLog, make_audit_sink
from .governance.guardrail import Guardrail
from .governance.quota import SessionQuota
from .handoff.manager import HandoffManager
from .knowledge.base import KnowledgeBase, KnowledgeBaseFactory
from .knowledge.retriever import Retriever
from .nlu.router import IntentRouter
from .observability.logger import get_logger
from .orchestrator.graph import Orchestrator
from .reception.channel import Channel, ChannelFactory
from .session.store.base import SessionStore
from .session.store.memory import InMemorySessionStore
from .skills.skill import Skill, SkillRegistry

logger = get_logger("runtime")


@dataclass
class Runtime:
    settings: Settings
    orchestrator: Orchestrator
    channels: List[Channel]


def build(settings: Settings) -> Runtime:
    # Knowledge bases
    kbs: List[KnowledgeBase] = []
    for spec in settings.kbs:
        kwargs = {"id": spec.id, "source": spec.source, "base_dir": settings.base_dir}
        kwargs.update(spec.options)
        kb = KnowledgeBaseFactory.create(spec.type, **kwargs)
        kbs.append(kb)
        logger.info("loaded KB id=%s type=%s", spec.id, spec.type)
    retriever = Retriever(kbs)

    # Skills
    enabled = list(settings.skills)
    if "fallback" not in enabled:
        enabled.append("fallback")
    skills: List[Skill] = []
    for name in enabled:
        skills.append(SkillRegistry.create(name))
        logger.info("enabled skill %s", name)

    # NLU router
    router = IntentRouter(retriever, enabled_skills=enabled)

    # Governance
    guardrail = Guardrail(
        block_patterns=settings.governance.guardrail_block_patterns,
        enabled=settings.governance.guardrail_enabled,
    )
    audit_log = AuditLog(
        sink=make_audit_sink(settings.governance.audit_sink),
        enabled=settings.governance.audit_enabled,
    )
    quota = SessionQuota(max_turns=settings.governance.session_max_turns)
    handoff = HandoffManager()

    # Session store (memory only for phase 0)
    store: SessionStore = InMemorySessionStore()

    orchestrator = Orchestrator(
        session_store=store,
        router=router,
        skills=skills,
        guardrail=guardrail,
        audit_log=audit_log,
        quota=quota,
        handoff=handoff,
    )

    # Channels
    channels: List[Channel] = []
    for spec in settings.channels:
        kwargs = dict(spec.options)
        kwargs.setdefault("tenant_id", settings.tenant.id)
        channels.append(ChannelFactory.create(spec.type, **kwargs))
        logger.info("attached channel %s", spec.type)

    return Runtime(settings=settings, orchestrator=orchestrator, channels=channels)
