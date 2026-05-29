"""Tenant and Workspace models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Tenant:
    id: str
    name: str
    workspaces: List["Workspace"] = field(default_factory=list)

    def workspace(self, workspace_id: str) -> Optional["Workspace"]:
        for ws in self.workspaces:
            if ws.id == workspace_id:
                return ws
        return None


@dataclass
class Workspace:
    id: str
    name: str
    enabled_channels: List[str] = field(default_factory=list)
    enabled_skills: List[str] = field(default_factory=list)
    enabled_kbs: List[str] = field(default_factory=list)
