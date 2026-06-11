from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Protocol

from .types import Message, ToolCall


class LLMClient(Protocol):
    def complete(self, messages: list[Message]) -> str:
        """Return the assistant text for the next turn."""


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Extract one or more JSON tool calls from an assistant message.

    The agent asks models to respond with either final prose or JSON like:
    {"tool": "read_file", "arguments": {"path": "README.md"}}
    {"tools": [{"tool": "read_file", "arguments": {...}}]}
    """

    payload = _extract_json(text)
    if payload is None:
        return []
    calls: list[ToolCall] = []
    if isinstance(payload, dict) and "tool" in payload:
        calls.append(ToolCall(str(payload["tool"]), dict(payload.get("arguments") or {})))
    elif isinstance(payload, dict) and "tools" in payload and isinstance(payload["tools"], list):
        for item in payload["tools"]:
            if isinstance(item, dict) and "tool" in item:
                calls.append(ToolCall(str(item["tool"]), dict(item.get("arguments") or {})))
    return calls


def _extract_json(text: str) -> object | None:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


class OpenAIResponsesClient:
    """Minimal OpenAI Responses API client using only Python's standard library."""

    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required unless you run with --mock")

    def complete(self, messages: list[Message]) -> str:
        input_messages = [{"role": m.role, "content": m.content} for m in messages]
        body = json.dumps({"model": self.model, "input": input_messages}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/responses",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        return _response_text(payload)


def _response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if chunks:
        return "\n".join(chunks)
    return json.dumps(payload, indent=2)


class MockClient:
    """Deterministic client for demos and tests without an API key."""

    def complete(self, messages: list[Message]) -> str:
        transcript = "\n".join(m.content for m in messages)
        if "TOOL RESULT" not in transcript:
            return json.dumps({"tool": "list_files", "arguments": {"glob": "*"}})
        if "README.md" not in transcript:
            return json.dumps({"tool": "write_file", "arguments": {"path": "README.md", "content": "# Demo\n\nCreated by simple-agent mock mode.\n"}})
        return "Done. I inspected the workspace and created a small README.md demo file."
