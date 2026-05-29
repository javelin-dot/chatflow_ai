"""Top-level runtime settings parsed from YAML.

Kept intentionally light — full Pydantic Settings can be added later when we
need env-var overrides at field level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .loader import load_yaml


@dataclass
class ChannelSpec:
    type: str
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KBSpec:
    id: str
    type: str
    source: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicySpec:
    type: str
    priority: int = 0
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantSpec:
    id: str
    name: str
    workspace: str = "default"


@dataclass
class GovernanceSpec:
    guardrail_enabled: bool = True
    guardrail_block_patterns: List[str] = field(default_factory=list)
    audit_enabled: bool = True
    audit_sink: str = "stdout"
    session_max_turns: int = 100


@dataclass
class Settings:
    version: str
    tenant: TenantSpec
    channels: List[ChannelSpec]
    kbs: List[KBSpec]
    skills: List[str]
    policies: List[PolicySpec]
    governance: GovernanceSpec
    llm: Dict[str, Any] = field(default_factory=dict)
    base_dir: Path = field(default_factory=Path.cwd)

    @classmethod
    def load(cls, path: str | Path) -> "Settings":
        path = Path(path)
        data = load_yaml(path)
        tenant_raw = data.get("tenant") or {}
        tenant = TenantSpec(
            id=tenant_raw.get("id", "default"),
            name=tenant_raw.get("name", "Default"),
            workspace=tenant_raw.get("workspace", "default"),
        )

        channels_raw = (data.get("reception") or {}).get("channels") or []
        channels = [
            ChannelSpec(type=c["type"], options={k: v for k, v in c.items() if k != "type"})
            for c in channels_raw
        ]

        kbs_raw = (data.get("knowledge") or {}).get("bases") or []
        kbs = [
            KBSpec(
                id=k["id"],
                type=k["type"],
                source=k.get("source"),
                options={kk: vv for kk, vv in k.items() if kk not in {"id", "type", "source"}},
            )
            for k in kbs_raw
        ]

        skills = (data.get("skills") or {}).get("enabled") or []

        policies_raw = data.get("policies") or []
        policies = [
            PolicySpec(
                type=p["type"],
                priority=p.get("priority", 0),
                options={k: v for k, v in p.items() if k not in {"type", "priority"}},
            )
            for p in policies_raw
        ]

        gov_raw = data.get("governance") or {}
        gr = gov_raw.get("guardrail") or {}
        au = gov_raw.get("audit") or {}
        qu = gov_raw.get("quota") or {}
        governance = GovernanceSpec(
            guardrail_enabled=gr.get("enabled", True),
            guardrail_block_patterns=gr.get("block_patterns") or [],
            audit_enabled=au.get("enabled", True),
            audit_sink=au.get("sink", "stdout"),
            session_max_turns=qu.get("session_max_turns", 100),
        )

        return cls(
            version=data.get("version", "0.1"),
            tenant=tenant,
            channels=channels,
            kbs=kbs,
            skills=skills,
            policies=policies,
            governance=governance,
            llm=data.get("llm") or {},
            base_dir=path.parent.resolve(),
        )
