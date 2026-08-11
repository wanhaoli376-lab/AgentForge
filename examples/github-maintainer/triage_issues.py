"""Run a real, read-only GitHub Issue triage task through AgentForge."""

import argparse
from pathlib import Path

from agentforge.config.loader import load_config
from agentforge.runtime import build_runtime


def _issue_limit(value: str) -> int:
    limit = int(value)
    if not 1 <= limit <= 100:
        raise argparse.ArgumentTypeError("limit must be between 1 and 100")
    return limit


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Triage open Issues without changing the GitHub repository."
    )
    parser.add_argument("owner", help="GitHub repository owner")
    parser.add_argument("repo", help="GitHub repository name")
    parser.add_argument("--limit", type=_issue_limit, default=10)
    parser.add_argument("--config", type=Path, help="Optional AgentForge YAML/TOML config")
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[2]
    config = load_config(args.config, workspace_root=repository_root)
    runtime = build_runtime(config)
    task = (
        f"Use the github-maintainer Skill to read up to {args.limit} open Issues from "
        f"{args.owner}/{args.repo}. For each Issue, suggest a category, priority, missing "
        "information, and possible duplicate search terms. Do not write, label, or close anything."
    )
    result = runtime.agent.run(task)
    if not result.ok:
        assert result.error is not None
        print(f"Error [{result.error.code}]: {result.error.message}")
        return 2
    print(result.answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
