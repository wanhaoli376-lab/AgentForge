# Changelog

All notable changes are documented here. AgentForge follows semantic versioning once stable release
tags begin.

## Unreleased

### Stability

- Raised the tested minimum versions of OpenAI, Pydantic, PyYAML, and pytest-cov.
- Added public-interface regression tests and an enforced 85% coverage floor.
- Added configurable models, credential environment variables, compatible API base URLs, and
  Responses or Chat Completions protocol selection without allowing credentials in config files.
- Added a manually approved, main-only live OpenAI Responses API smoke workflow whose Environment
  secret is unavailable to pull requests and normal CI.

## 0.1.0a1 - 2026-08-12

### Features

- Added the single-agent Skill selection, planning, Plugin execution, and synthesis loop.
- Added validated Markdown Skills and four built-in maintenance/developer Skills.
- Added Filesystem, Shell, Python, and read-only GitHub Plugins.
- Added CLI one-shot, interactive, doctor, Skill, and Plugin commands.

### Security

- Added action-level permissions and least-privilege defaults.
- Added path, command, Python AST, network, subprocess, and secret-redaction policies.
- Added attack-oriented traversal, injection, permission, timeout, SSRF, and secret tests.
- Added a documented threat model and read-only, SHA-pinned CI workflow.

### Documentation

- Added architecture, extension development, security, Codex Security, OpenAI maintenance, project
  overview, project analysis, contribution, conduct, and security reporting guides.

### Distribution

- Renamed the PyPI distribution to `agentforge-secure` because the original distribution name was
  already owned by an unrelated project. The Python package and CLI remain `agentforge`.
- Added package validation to pull-request CI and a least-privilege, Trusted Publishing workflow
  for attested PyPI uploads from GitHub Releases after maintainer approval.
