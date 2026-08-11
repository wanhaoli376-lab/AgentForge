# GitHub Maintainer: Issue Triage

This is a real, read-only AgentForge workflow. It lets the model select the built-in
`github-maintainer` Skill, plan `github.list_issues`, receive bounded structured Issue data, and
draft triage advice. It does not post comments, labels, or closures.

From the repository root:

```bash
python -m pip install -e .
export OPENAI_API_KEY="your-key"
# Optional for private repositories or higher API limits:
export GITHUB_TOKEN="a-scoped-token"

python examples/github-maintainer/triage_issues.py wanhaoli376-lab AgentForge --limit 10
```

Windows PowerShell uses `$env:OPENAI_API_KEY = "your-key"` and the equivalent for
`GITHUB_TOKEN`.

The example overrides the workspace root to this repository so the built-in Skills are available.
`github_read` is enabled by default; `github_write`, Shell, Python, filesystem writes, and general
network access remain disabled. Review every model classification before acting on it.
