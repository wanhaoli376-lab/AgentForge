# Contributing to AgentForge

Thank you for helping build a reusable, security-aware agent framework. Contributions are
welcome as focused code changes, Skills, Plugins, tests, documentation, and threat-model
improvements.

## Before you start

1. Search existing Issues and pull requests.
2. Open an Issue for a large interface change or new high-risk capability.
3. Keep one pull request focused on one problem.
4. Never include credentials, private repository data, or generated secret files.

Small fixes, tests, and documentation improvements can go directly to a pull request.

## Development setup

```bash
git clone https://github.com/wanhaoli376-lab/AgentForge.git
cd AgentForge
python -m venv .venv
python -m pip install -e ".[dev]"
```

Run the same checks as CI:

```bash
ruff check src tests
mypy src
pytest
pytest tests/security
```

Tests should exercise public interfaces and observable behavior. For a bug, add a regression
test that fails before the fix. Security fixes should include an attack-oriented test under
`tests/security/` whenever practical.

## Code contributions

- Support Python 3.11 and newer.
- Keep interfaces small and put validation and policy in the module that owns it.
- Use Pydantic models for external/configuration data and structured Plugin arguments.
- Do not use `shell=True`, concatenate model output into commands, or run model-generated code
  in the main Agent process.
- Do not move permission checks into prompts. Code must enforce them.
- Keep credentials out of logs, exceptions, fixtures, snapshots, and examples.
- Update documentation when behavior, permissions, config, or limitations change.

## Contributing a Skill

A Skill contribution needs:

- one directory under `skills/` containing `SKILL.md`;
- valid name, version, description, author, required Plugins, and keywords;
- explicit security guidance for untrusted input;
- a loader/selection test when introducing new metadata behavior;
- no claim that Skill text can grant a permission.

Follow [Skill Development](docs/skill-development.md) and the
[`project-explainer` template](examples/skills/project-explainer/).

## Contributing a Plugin

A Plugin contribution needs:

- a narrow action interface with strict Pydantic argument models;
- per-action permission declarations;
- structured, bounded results;
- unit tests plus security tests for paths, commands, network, credentials, or writes it touches;
- user and security documentation;
- a manifest describing name, version, author, actions, permissions, and entry point.

New subprocess, network, filesystem-write, or GitHub-write behavior receives additional human
review. A Plugin is ordinary Python once imported; metadata is not an OS sandbox. Unknown Plugin
code is never auto-installed or auto-loaded by the v0.1 runtime.

## Pull request process

Pull requests should include:

- the problem and intended behavior;
- the security impact and new permissions, or “none”;
- tests run locally;
- documentation changes;
- a concise note about backward compatibility.

CI uses read-only repository permissions. It must not be changed to `pull_request_target` or
given secrets merely to make an untrusted contribution pass. Maintainers may request smaller
commits, stronger tests, or threat-model updates before merge.

By contributing, you agree that your contribution is licensed under Apache-2.0.
