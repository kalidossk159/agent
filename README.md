# Simple Coding Agent

A tiny terminal coding agent for learning how modern agents work. It is intentionally small, dependency-free, and readable, but it includes simplified versions of the building blocks used by today's coding agents:

- **ReAct loop**: the model alternates between reasoning, tool calls, and observations.
- **Structured tool calls**: the model requests tools with JSON instead of free-form shell text.
- **Workspace tools**: list files, read files, write files, search with ripgrep, and run shell commands.
- **Guardrails**: file access is restricted to the workspace, destructive shell commands are blocked unless you pass `--yes`, and `--dry-run` previews actions.
- **Memory and traces**: transcripts are saved in `.simple-agent/runs/`, and optional long-term notes can live in `.simple-agent/memory.md`.
- **Verification hook**: pass `--test-command` to run tests or checks after the agent loop.
- **Mock mode**: run the agent without an API key to see the mechanics.

## Quick start

```bash
python -m simple_coding_agent.cli --mock "create a tiny README demo"
```

To use a real model, set your API key and run:

```bash
export OPENAI_API_KEY="..."
python -m simple_coding_agent.cli "add a hello world script"
```

After installation, the console script is also available:

```bash
pip install -e .
simple-agent --mock "inspect this project"
```

## How the agent works

1. `cli.py` parses terminal flags and creates an `AgentConfig`.
2. `agent.py` builds a system prompt that lists available tools and runs the model/tool loop.
3. `llm.py` calls the OpenAI Responses API or the deterministic mock client.
4. `tools.py` implements the actual file and shell operations.
5. Every tool result is appended back into the transcript so the model can decide the next action.

The important teaching idea is that an agent is not magic. It is a loop:

```text
user task -> model -> structured tool call -> tool result -> model -> ... -> final answer
```

## Example tasks

```bash
simple-agent --mock "show me the project files"
simple-agent "add tests for the calculator module" --test-command "python -m pytest"
simple-agent --dry-run "rename the CLI flag in this package"
```

## Tool-call format

The model is instructed to call tools by returning JSON only:

```json
{"tool": "read_file", "arguments": {"path": "README.md"}}
```

It can also request independent calls together:

```json
{
  "tools": [
    {"tool": "list_files", "arguments": {"glob": "*.py"}},
    {"tool": "search", "arguments": {"pattern": "TODO"}}
  ]
}
```

## Safety notes

This project is for learning. It deliberately keeps safety controls understandable rather than exhaustive. Run it in a Git repository, review diffs, and prefer `--dry-run` while experimenting.
