<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

# AgentForge

[![CI](https://github.com/wanhaoli376-lab/AgentForge/actions/workflows/ci.yml/badge.svg)](https://github.com/wanhaoli376-lab/AgentForge/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

An open-source, extensible and security-aware AI agent framework with Skills, Plugins and sandboxed tool execution.

> **Project status: alpha.** AgentForge is usable as a local CLI and framework, but its
> subprocess controls are defense in depth—not complete operating-system or container
> isolation. Do not run untrusted Plugins or unreviewed code on a sensitive machine.

## Why AgentForge

Many agent projects couple prompts, tools, code execution, and network access into one
application. That makes capabilities hard to reuse and leaves authorization decisions too
close to model output. AgentForge separates those concerns:

- **Agent Core** understands a task, selects Skills, plans bounded Plugin calls, and summarizes
  structured results.
- **Skills** are versioned Markdown guidance for a class of tasks. They never grant permissions.
- **Plugins** expose validated actions through one interface. The model receives no direct OS
  handle.
- **Permission and policy modules** make the final authorization decision in code.

The result is a reusable foundation for local automation, open-source maintenance, and
security research—not a fixed AI application.

## Features

| Capability | Status | Notes |
| --- | --- | --- |
| Single-agent core | Implemented | Skill selection → plan → Plugin execution → final answer |
| Markdown Skills | Implemented | YAML metadata, validation, keyword/LLM selection |
| Plugin interface and registry | Implemented | Action schemas, permission declarations, structured results |
| Filesystem Plugin | Implemented | Workspace confinement, traversal/symlink checks, sensitive-path blocks |
| Shell Plugin | Experimental | argv only, `shell=False`, allowlist, timeout, filtered environment |
| Python Plugin | Experimental | AST policy plus a separate `python -I -S` child process |
| GitHub Plugin | Implemented, read-only | Repositories, Issues, PRs, files/diffs, commits, local Issue drafts |
| Secret redaction | Implemented | Common OpenAI, GitHub, Bearer, AWS, and explicit runtime secrets |
| Network policy | Implemented | HTTPS/domain allowlist and private/local/metadata IP denial |
| General Web/Network Plugin | Not implemented | Planned; network access remains off by default |
| Plugin/Skill marketplace | Planned | Targeted for later releases |

## Architecture

```text
User
  ↓
Agent Core
  ↓
Untrusted Skill guidance
  ↓
Validated execution plan
  ↓
Plugin interface
  ↓
Permission + policy layer
  ↓
Restricted subprocess / API adapter
  ↓
Filesystem / Shell / Python / GitHub
```

The LLM proposes actions; it does not decide whether they are authorized. Every Plugin action
is checked against configured permissions and validated arguments before implementation code
runs. See [Architecture](docs/architecture.md) and the [Security Model](docs/security-model.md).

## Quick start

Requirement: Python 3.11 or newer.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the current alpha release and inspect the CLI. The distribution is named
`agentforge-secure`, while the command and Python package remain `agentforge`.

```bash
python -m pip install --pre agentforge-secure
agentforge --help
agentforge doctor
```

Set the OpenAI key in your shell—never in source control:

```bash
# macOS / Linux
export OPENAI_API_KEY="your-key"

# Windows PowerShell
$env:OPENAI_API_KEY = "your-key"
```

Run a task:

```bash
agentforge run "summarize the current repository"
```

Or start interactive mode:

```text
$ agentforge
AgentForge > run the tests and explain why they failed
```

Shell and Python execution are disabled by default. Copy the example configuration only when
you need to make an explicit permission decision:

```bash
cp agentforge.example.yaml agentforge.yaml
agentforge --config agentforge.yaml run "run the tests and explain failures"
```

## Configuration

AgentForge reads YAML or TOML through `--config`. The defaults follow least privilege:

```yaml
agent:
  model: gpt-5.6-luna
  api_mode: responses
  api_key_env: OPENAI_API_KEY
workspace:
  root: .
  skills_dir: skills
permissions:
  filesystem_read: true
  filesystem_write: false
  filesystem_delete: false
  shell_execute: false
  python_execute: false
  network_access: false
  github_read: true
  github_write: false
security:
  redact_secrets: true
  command_timeout: 30
  max_output_chars: 50000
```

The model provider is configurable. Keep `responses` for OpenAI or another Responses-compatible
endpoint; use `chat_completions` for an OpenAI-compatible Chat Completions endpoint. For example:

```yaml
agent:
  model: provider-model
  api_mode: chat_completions
  base_url: https://provider.example/v1
  api_key_env: MY_LLM_API_KEY
```

```bash
export MY_LLM_API_KEY="your-provider-key"
agentforge --config agentforge.yaml doctor
```

Credentials are intentionally unsupported in config files: `api_key_env` stores only an
environment variable name, never the key itself. Remote provider URLs must use HTTPS; plain HTTP
is allowed only for loopback development services. See [LLM Provider Configuration](docs/llm-providers.md).
The optional `GITHUB_TOKEN` remains separate. The GitHub Plugin can read public repositories
without it, subject to GitHub's unauthenticated rate limits.

## Skills

A Skill describes how to approach a task. It is a versioned `SKILL.md` with strict YAML front
matter and Markdown instructions:

```markdown
---
name: test-runner
version: 0.1.0
description: Run project tests and explain failures.
author: AgentForge contributors
required_plugins: [filesystem, shell]
keywords: [test, pytest, failure]
---
# Test Runner

Run tests only through the Shell Plugin and explain the first actionable failure.
```

Built-in Skills:

- `repository-summary`
- `test-runner`
- `code-review`
- `github-maintainer`

Skill text is untrusted input. It may influence a model proposal, but it cannot bypass Plugin
schemas, path policy, command policy, or permissions. See [Skill Development](docs/skill-development.md)
and the copyable [project-explainer example](examples/skills/project-explainer/).

## Plugins

| Plugin | Actions | Required permission |
| --- | --- | --- |
| `filesystem` | list, read, create, write, delete | Per-action filesystem permission |
| `shell` | run | `shell.execute` |
| `python` | run | `python.execute` |
| `github` | repository, Issues, PRs, diffs, commits, draft Issue | `github.read`; drafts are local |

Community Plugins subclass `Plugin`, define Pydantic action models and permission metadata,
then register through `PluginRegistry`. Dynamic entry-point discovery is planned, not yet
implemented. See [Plugin Development](docs/plugin-development.md) and the
[hello_plugin example](examples/plugins/hello_plugin/).

## GitHub maintainer workflow

The `github-maintainer` Skill supports:

- Issue triage into `bug`, `feature`, `question`, `documentation`, `security`, or
  `duplicate candidate`;
- PR summaries with changed modules, risks, suggested tests, and security-sensitive areas;
- release notes grouped into Features, Bug Fixes, Security, Documentation, and Breaking Changes;
- documentation drift checks.

It does not automatically close Issues, merge PRs, or submit Issue drafts. Try the
[runnable triage example](examples/github-maintainer/README.md).

## Security

AgentForge combines LLM output, third-party text, filesystem access, subprocesses, API tokens,
and community extensions. Those are real attack surfaces.

Security controls include:

- least-privilege defaults and action-level permission checks;
- canonical workspace path resolution and symlink-escape checks;
- argv-only subprocesses, command allowlists, timeouts, filtered environments, and output caps;
- conservative Python AST checks in a separate process;
- HTTPS/domain allowlists and denial of localhost, private, link-local, reserved, and metadata IPs;
- secret redaction before logs, LLM context, and Agent tool-result summaries;
- GET-only GitHub API behavior in v0.1;
- tests for traversal, injection, prompt-injection impact, permission bypass, and secret leakage.

Important limitations:

- `ProcessSandbox` is **not** a kernel sandbox, VM, seccomp profile, or container.
- Python AST validation is bypass-resistant guidance, not a proof of safe arbitrary Python.
- an imported third-party Plugin is ordinary Python and can act before the framework can mediate it;
- local tests and project code can themselves be malicious when Shell execution is enabled;
- DNS validation cannot by itself eliminate every rebinding or proxy-layer risk.

Read [SECURITY.md](SECURITY.md), the [Security Model](docs/security-model.md), and the
[Threat Model](docs/threat-model.md) before enabling high-risk permissions.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
pytest
pytest tests/security
```

CI runs lint, strict type checking, the full test suite, the dedicated security suite, and PyPI
distribution validation. Workflows use read-only repository permissions and do not expose secrets
to pull requests.
Maintainers can use the separately approved [live API smoke test](docs/live-api-testing.md) to make
one real OpenAI Responses API request without exposing its Environment secret to normal CI.
Maintainers can follow the [Release Guide](docs/releasing.md) for the `agentforge-secure` PyPI
distribution.

## Contributing

Contributions are welcome in the form of Skills, Plugins, tests, documentation, and focused
framework improvements. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Security-sensitive
changes need regression tests and human review; unknown pull requests are never a reason to
enable high-risk CI credentials or execute privileged automation.

## Roadmap

- **v0.1:** CLI, Agent Core, Skills, Plugins, permissions, restricted local execution
- **v0.2:** stronger process isolation adapters, richer GitHub maintenance workflows
- **v0.3:** signed/verified Plugin registry design
- **v0.4:** Skill registry, provenance metadata, and distribution tooling

Roadmap items are plans, not current capabilities. See [Project Overview](docs/project-overview.md)
for the intended ecosystem.

## License

Copyright 2026 wanhaoli376-lab and AgentForge contributors.

Licensed under the [Apache License 2.0](LICENSE).
