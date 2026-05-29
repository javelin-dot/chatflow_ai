"""LIFO dialogue stack (borrowed from CALM-style design).

Each frame represents an active context: a running flow, a knowledge-answer
in progress, a handoff to human, etc. Interrupts push, completions pop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StackFrame:
    type: str
    data: dict = field(default_factory=dict)


@dataclass
class DialogueStack:
    frames: List[StackFrame] = field(default_factory=list)

    def push(self, frame: StackFrame) -> None:
        self.frames.append(frame)

    def pop(self) -> Optional[StackFrame]:
        return self.frames.pop() if self.frames else None

    def top(self) -> Optional[StackFrame]:
        return self.frames[-1] if self.frames else None

    def is_empty(self) -> bool:
        return not self.frames
