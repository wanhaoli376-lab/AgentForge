# Project Overview

## Purpose

AgentForge is a Python framework and CLI for building agents whose reasoning, task guidance, real
capabilities, and authorization are separate modules. It addresses two recurring problems:

1. agent applications hard-code every tool and workflow, making reuse and community extension
   difficult;
2. model output is treated too much like trusted control flow, leaving weak or inconsistent
   boundaries around files, commands, network access, and credentials.

AgentForge provides a reusable Agent Core, versioned Skills, validated Plugins, and a code-enforced
permission/policy model. Projects can embed those parts to build their own local automation instead
of forking one fixed AI application.

## Intended users

- **AI agent developers** who need a small orchestration core with explicit capability seams.
- **Python developers** building local developer tools and repository automation.
- **Open-source maintainers** triaging Issues, reviewing PR context, producing release notes, and
  maintaining documentation.
- **Plugin developers** adding bounded capabilities such as databases, Docker, or SaaS APIs.
- **Skill developers** packaging task methods without embedding executable code.
- **Security researchers** studying prompt injection paths that end in real tool execution.
- **Local automation users** who want inspectable configuration and least-privilege defaults.

## Reusable layers

```text
Reusable Agent Core
        +
Reusable Skills
        +
Reusable Plugins
        +
Security Permission Model
```

The value is compositional. A documentation agent and a GitHub-maintenance agent can share the
same filesystem adapter, secret filter, and permission system while loading different Skills. A
new database Plugin can be reused by multiple Skills without placing database credentials in
prompts.

## Current capabilities

- CLI one-shot and interactive tasks;
- OpenAI-backed Skill selection, planning, and final synthesis;
- Markdown Skill validation and registry;
- explicit Plugin registry and action metadata;
- workspace filesystem access;
- experimental restricted Shell and Python processes;
- GET-only GitHub repository, Issue, PR, diff/file, and commit data;
- local Issue draft construction;
- permission, path, command, Python, network, and secret policy modules;
- unit, integration, and security tests;
- contribution, conduct, security, threat-model, and development documentation.

## Ecosystem direction

Potential community extensions include:

- Docker and container sandbox Plugins;
- database Plugins with query allowlists and read-only modes;
- Slack and Notion Plugins;
- COMSOL, data analysis, documentation, and security review Skills;
- Plugin provenance, signatures, review state, and revocation;
- Skill distribution and compatibility metadata.

These are ecosystem opportunities, not v0.1 claims. New capabilities must retain explicit
permissions and honest residual-risk documentation.

## Contribution model

```text
Pull Request
    ↓
Read-only CI
    ↓
Lint + type checks + tests + security tests
    ↓
Human code and permission review
    ↓
Merge
```

AgentForge does not automatically execute or install an unknown Plugin contribution. Tests in an
untrusted pull request run only in GitHub's CI runner with minimal token permissions and no project
secrets. Security-sensitive changes require attack-oriented regression tests.
