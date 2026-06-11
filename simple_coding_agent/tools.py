from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .types import ToolResult


MAX_FILE_BYTES = 80_000
MAX_OUTPUT_CHARS = 20_000


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    run: Callable[[dict], ToolResult]


def _trim(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return f"{text[:limit]}\n... <trimmed {omitted} characters>"


class WorkspaceTools:
    """Small, safe-ish tools for inspecting and changing one workspace."""

    def __init__(self, workspace: Path, auto_yes: bool = False, dry_run: bool = False):
        self.workspace = workspace.resolve()
        self.auto_yes = auto_yes
        self.dry_run = dry_run

    def registry(self) -> dict[str, Tool]:
        return {
            "list_files": Tool(
                "list_files",
                "List tracked-looking project files using ripgrep when available.",
                {"type": "object", "properties": {"glob": {"type": "string"}}},
                self.list_files,
            ),
            "read_file": Tool(
                "read_file",
                "Read a UTF-8 text file from the workspace.",
                {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
                self.read_file,
            ),
            "write_file": Tool(
                "write_file",
                "Create or replace a UTF-8 text file in the workspace.",
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
                self.write_file,
            ),
            "search": Tool(
                "search",
                "Search workspace text with ripgrep.",
                {
                    "type": "object",
                    "properties": {"pattern": {"type": "string"}, "glob": {"type": "string"}},
                    "required": ["pattern"],
                },
                self.search,
            ),
            "run_shell": Tool(
                "run_shell",
                "Run a shell command in the workspace. Use for tests, formatters, and git diff/status.",
                {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
                self.run_shell,
            ),
        }

    def _path(self, user_path: str) -> Path:
        path = (self.workspace / user_path).resolve()
        if path != self.workspace and self.workspace not in path.parents:
            raise ValueError(f"Path escapes workspace: {user_path}")
        return path

    def list_files(self, args: dict) -> ToolResult:
        glob = args.get("glob") or "*"
        command = ["rg", "--files", "-g", glob]
        try:
            proc = subprocess.run(command, cwd=self.workspace, text=True, capture_output=True, timeout=15)
            if proc.returncode in (0, 1):
                return ToolResult("list_files", True, _trim(proc.stdout or "<no files>"))
            return ToolResult("list_files", False, _trim(proc.stderr))
        except FileNotFoundError:
            files = [str(p.relative_to(self.workspace)) for p in self.workspace.rglob("*") if p.is_file()]
            return ToolResult("list_files", True, _trim("\n".join(sorted(files)) or "<no files>"))
        except Exception as exc:
            return ToolResult("list_files", False, str(exc))

    def read_file(self, args: dict) -> ToolResult:
        try:
            path = self._path(str(args["path"]))
            if path.stat().st_size > MAX_FILE_BYTES:
                return ToolResult("read_file", False, f"File is too large for this teaching agent: {path}")
            return ToolResult("read_file", True, path.read_text(encoding="utf-8"))
        except Exception as exc:
            return ToolResult("read_file", False, str(exc))

    def write_file(self, args: dict) -> ToolResult:
        rel = str(args["path"])
        content = str(args["content"])
        try:
            path = self._path(rel)
            if self.dry_run:
                return ToolResult("write_file", True, f"DRY RUN: would write {rel} ({len(content)} chars)")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult("write_file", True, f"Wrote {rel} ({len(content)} chars)")
        except Exception as exc:
            return ToolResult("write_file", False, str(exc))

    def search(self, args: dict) -> ToolResult:
        pattern = str(args["pattern"])
        command = ["rg", "--line-number", "--hidden", pattern]
        if args.get("glob"):
            command.extend(["-g", str(args["glob"])])
        try:
            proc = subprocess.run(command, cwd=self.workspace, text=True, capture_output=True, timeout=15)
            if proc.returncode in (0, 1):
                return ToolResult("search", True, _trim(proc.stdout or "<no matches>"))
            return ToolResult("search", False, _trim(proc.stderr))
        except Exception as exc:
            return ToolResult("search", False, str(exc))

    def run_shell(self, args: dict) -> ToolResult:
        command = str(args["command"])
        try:
            if self.dry_run:
                return ToolResult("run_shell", True, f"DRY RUN: would run {command!r}")
            if not self.auto_yes and _looks_destructive(command):
                return ToolResult(
                    "run_shell",
                    False,
                    "Refusing likely destructive command without --yes. Run the agent with --yes if you trust it.",
                )
            proc = subprocess.run(command, cwd=self.workspace, shell=True, text=True, capture_output=True, timeout=120)
            output = f"$ {command}\nexit={proc.returncode}\n\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            return ToolResult("run_shell", proc.returncode == 0, _trim(output))
        except Exception as exc:
            return ToolResult("run_shell", False, str(exc))

    def describe_tools_for_prompt(self) -> str:
        return json.dumps(
            [
                {"name": tool.name, "description": tool.description, "schema": tool.schema}
                for tool in self.registry().values()
            ],
            indent=2,
        )


def _looks_destructive(command: str) -> bool:
    """Intentionally simple guardrail for a teaching agent."""

    tokens = shlex.split(command, posix=os.name != "nt") if command.strip() else []
    joined = " ".join(tokens)
    risky_fragments = ["rm -rf", "git reset --hard", "git clean", "sudo", "mkfs", ":(){"]
    return any(fragment in joined for fragment in risky_fragments)
