from __future__ import annotations

import argparse
from pathlib import Path

from .agent import CodingAgent
from .llm import MockClient, OpenAIResponsesClient
from .types import AgentConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="simple-agent",
        description="Run a small educational coding agent in your terminal.",
    )
    parser.add_argument("task", nargs="*", help="Coding task to perform. If omitted, you will be prompted.")
    parser.add_argument("--workspace", default=".", help="Workspace directory the agent may inspect and edit.")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model name to use.")
    parser.add_argument("--max-steps", type=int, default=12, help="Maximum model/tool iterations.")
    parser.add_argument("--yes", action="store_true", help="Allow commands that the simple guardrail considers destructive.")
    parser.add_argument("--dry-run", action="store_true", help="Show intended writes/commands without changing files.")
    parser.add_argument("--mock", action="store_true", help="Use a deterministic fake model; no API key needed.")
    parser.add_argument("--test-command", help="Optional command to run after the agent loop, e.g. 'pytest'.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    task = " ".join(args.task).strip() or input("Task: ").strip()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    config = AgentConfig(
        workspace=workspace,
        model=args.model,
        max_steps=args.max_steps,
        auto_yes=args.yes,
        dry_run=args.dry_run,
        mock=args.mock,
        test_command=args.test_command,
    )
    client = MockClient() if args.mock else OpenAIResponsesClient(model=args.model)
    agent = CodingAgent(config, client)
    agent.run(task)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
