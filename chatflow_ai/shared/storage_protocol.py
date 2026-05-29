# -*- coding: utf-8 -*-
"""Abstract storage protocol for MVP JSON backends.

All concrete storage classes (JSON file, SQLAlchemy, etc.) should implement
these interfaces so the rest of the codebase remains agnostic to the
underlying persistence mechanism.

Migration path to a real database:
1. Implement SqlAlchemyStorage following the same interfaces
2. Swap the default storage in get_registry() / WorkflowStorage()
3. Run a one-time data migration from JSON files to DB tables
"""

from __future__ import annotations

from typing import Protocol


class RegistryStorageProtocol(Protocol):
    """Protocol for service registry persistence."""

    async def save(self, spec) -> None: ...
    async def load(self, name: str): ...
    async def list_names(self) -> list[str]: ...
    async def delete(self, name: str) -> bool: ...


class WorkflowStorageProtocol(Protocol):
    """Protocol for workflow template / execution persistence."""

    async def save_workflow(self, workflow) -> None: ...
    async def load_workflow(self, workflow_id: str): ...
    async def list_workflow_ids(self) -> list[str]: ...
    async def delete_workflow(self, workflow_id: str) -> bool: ...
    async def save_execution(self, context) -> None: ...
    async def load_execution(self, run_id: str): ...
