from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from .llm import LLMClient, parse_tool_calls
from .tools import WorkspaceTools
from .types import AgentConfig, Message, ToolResult


SYSTEM_TEMPLATE = """You are a compact educational coding agent running in a terminal.

Your job is to help modify code in the user's workspace while demonstrating modern agent behavior in a simple way.

Capabilities available as JSON tools:
{tools}

Operating loop:
1. Understand the task and make a brief plan internally.
2. Inspect before editing: list files, read relevant files, and search when needed.
3. Change files with write_file. Keep changes small and explainable.
4. Run tests or checks with run_shell when useful.
5. Finish with a concise summary and mention changed files.

Rules:
- To call a tool, respond with ONLY JSON: {{"tool": "tool_name", "arguments": {{...}}}}.
- You may call multiple independent tools with: {{"tools": [{{"tool": "...", "arguments": {{...}}}}]}}.
- If no more tools are needed, respond normally with your final answer.
- Stay inside the workspace. Do not hide failures. Prefer simple, readable code.
- Current UTC time: {now}.
"""


class CodingAgent:
    """A tiny ReAct-style coding agent with tools, memory, and transcripts."""

    def __init__(self, config: AgentConfig, client: LLMClient):
        self.config = config
        self.client = client
        self.tools = WorkspaceTools(config.workspace, auto_yes=config.auto_yes, dry_run=config.dry_run)
        self.registry = self.tools.registry()
        memory_path = config.memory_file or config.workspace / ".simple-agent" / "memory.md"
        self.memory_path = memory_path
        self.messages: list[Message] = [self._system_message()]

    def run(self, task: str) -> str:
        self._load_memory()
        self.messages.append(Message("user", task))
        final = ""
        for step in range(1, self.config.max_steps + 1):
            print(f"\n--- agent step {step}/{self.config.max_steps} ---")
            assistant_text = self.client.complete(self.messages)
            print(assistant_text)
            self.messages.append(Message("assistant", assistant_text))
            calls = parse_tool_calls(assistant_text)
            if not calls:
                final = assistant_text
                break
            for call in calls:
                result = self._run_tool(call.name, call.arguments)
                tool_message = _format_tool_result(result)
                print(tool_message)
                self.messages.append(Message("tool", tool_message))
        else:
            final = "Stopped because max_steps was reached. Increase --max-steps if needed."
            print(final)
        if self.config.test_command:
            test_result = self.registry["run_shell"].run({"command": self.config.test_command})
            print(_format_tool_result(test_result))
        self._save_transcript(task)
        return final

    def _system_message(self) -> Message:
        return Message(
            "system",
            SYSTEM_TEMPLATE.format(
                tools=self.tools.describe_tools_for_prompt(),
                now=dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )

    def _load_memory(self) -> None:
        if self.memory_path.exists():
            memory = self.memory_path.read_text(encoding="utf-8")
            self.messages.append(Message("user", f"Long-term workspace memory:\n{memory}"))

    def _run_tool(self, name: str, arguments: dict) -> ToolResult:
        tool = self.registry.get(name)
        if tool is None:
            return ToolResult(name, False, f"Unknown tool: {name}. Available: {', '.join(self.registry)}")
        return tool.run(arguments)

    def _save_transcript(self, task: str) -> None:
        log_dir = self.config.workspace / ".simple-agent" / "runs"
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        data = {
            "task": task,
            "model": self.config.model,
            "messages": [message.__dict__ for message in self.messages],
        }
        (log_dir / f"{stamp}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def _format_tool_result(result: ToolResult) -> str:
    status = "ok" if result.ok else "error"
    return f"TOOL RESULT {result.name} ({status}):\n{result.output}"
