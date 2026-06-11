from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    """One chat message in the agent transcript."""

    role: Role
    content: str


@dataclass
class ToolCall:
    """A structured request from the model to run a tool."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """The result returned to the model after a tool runs."""

    name: str
    ok: bool
    output: str


@dataclass
class AgentConfig:
    """Runtime configuration for the terminal agent."""

    workspace: Path
    model: str
    max_steps: int = 12
    auto_yes: bool = False
    dry_run: bool = False
    mock: bool = False
    test_command: str | None = None
    memory_file: Path | None = None
