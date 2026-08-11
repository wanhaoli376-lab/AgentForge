# AgentForge Project Analysis

## 1. Primary use and problem solved

AgentForge is an open-source, extensible, security-aware AI Agent framework for Python 3.11+. Its
main interface is a CLI, and its reusable interfaces can also be embedded in other Python tools.

The repository solves the coupling problem found in many agent applications: prompts, tools,
filesystem access, shell execution, network calls, and provider code are often written into one
control loop. That makes extension difficult and lets model decisions sit too close to operating
system capabilities.

AgentForge separates:

- natural-language planning in the Agent Core;
- task method in Markdown Skills;
- real capabilities in Plugins;
- final authorization in permissions and policy code;
- provider access in one LLM client.

The LLM can propose a call but cannot grant it. This makes the framework suitable for local
developer automation, open-source maintenance, extension experiments, and security research.

## 2. GitHub Stars, Forks, and Contributors

This is a new repository. No values are invented in this analysis.

- Stars: available from GitHub after publication
- Forks: available from GitHub after publication
- Contributors: available from GitHub after publication

The GitHub API can provide these values dynamically after publication. They should not be copied
into documentation as static claims unless a timestamp and source are included.

## 3. Main functions, modules, and components

### Agent Core

`Agent.run(task)` selects Skills, requests a bounded JSON plan, executes each validated step through
the Plugin registry, and asks the model to summarize redacted structured results.

### Skill System

The loader scans `SKILL.md`, safely parses YAML metadata, enforces version/author/size/schema rules,
rejects duplicates, and registers text as untrusted guidance. Selection uses metadata, keywords,
and the LLM; no vector database is required.

### Plugin System

The base Plugin interface declares action models and per-action permissions. It validates action,
permission, and arguments before `_execute`. The registry exposes safe manifests to the planner.

### CLI

The `agentforge` command supports one-shot runs, interactive mode, `doctor`, version reporting,
Skill listing, Plugin listing, YAML/TOML config, and structured JSON results.

### Permission Layer

Capabilities include filesystem read/write/delete, Shell, Python, general network, and GitHub
read/write. Defaults follow least privilege. Permissions are enforced in code, not prompts.

### Restricted execution / Sandbox

`ProcessSandbox` uses argv, `shell=False`, filtered environment, fixed cwd, no stdin, timeout,
bounded output, and secret redaction. It is not full OS isolation. `PythonCodePolicy` adds
experimental AST restrictions before a separate Python child process.

### GitHub integration

The GitHub Plugin performs bounded GET requests for repository metadata, Issues, Pull Requests, PR
files/diffs, and commits. It can produce local Issue draft data but performs no remote write in
v0.1. `GITHUB_TOKEN` is optional for public data and is read only from the environment.

## 4. User groups

- AI developers building agents with explicit tool seams;
- Python developers building developer tools and automation;
- open-source maintainers working with Issues, PRs, releases, and docs;
- Plugin developers contributing reusable real capabilities;
- Skill developers contributing reusable task guidance;
- security researchers analyzing prompt-to-capability paths;
- local users who want configurable, inspectable AI automation.

## 5. Value to the open-source ecosystem

AgentForge does not provide only one fixed AI App. It provides reusable layers:

```text
Agent Core + Skills + Plugins + Permission/Policy Model
```

Third parties can contribute one bounded Plugin and make it usable by multiple Skills, or contribute
a Skill that reuses existing Plugins. Clear manifests, tests, docs, and permission review make
extension work visible to maintainers. The architecture also gives security research a concrete
target: the complete path from malicious text to a real file, process, network, or GitHub action.

## 6. Capability checklist

| Capability | Involved? | Current implementation |
| --- | --- | --- |
| AI Agent | Yes | Single-agent selection, planning, execution, synthesis |
| Plugin | Yes | Base interface, registry, four built-ins |
| Skill | Yes | Markdown format, loader, registry, four built-ins |
| CLI | Yes | One-shot, interactive, diagnostics, inspection |
| Developer tools | Yes | Repository analysis, tests, review and maintenance Skills |
| Automation | Yes | Planned Plugin calls and structured results |
| Code execution | Yes, experimental | Restricted Shell and Python child processes, default off |
| Third-party contributions | Yes | Explicit Skill/Plugin examples and contribution checks |

## 7. Potential security risks

### Malicious code

An allowed Python snippet, test suite, or imported Plugin can execute harmful behavior. AST checks
and subprocess restrictions reduce accidental paths but do not replace a container or VM.

### Malicious scripts

Repository tests and scripts may read or modify anything the child OS account can access. Shell and
Python permissions are disabled by default; hostile repositories should use disposable isolation.

### Prompt injection

A task, Skill, README, Issue, PR, or diff may tell the model to ignore rules. Prompt hierarchy helps,
but schemas, permissions, path/command/network policy, and tests enforce the real boundary.

### API key leakage

Keys could leak through logs, exception bodies, tool results, model context, config, or child
environment. AgentForge uses environment-only credentials, filters child environment, and redacts
common/exact values, but transformed secrets remain a residual risk.

### Unauthorized network requests

SSRF could target localhost, private services, or cloud metadata. The network policy requires HTTPS,
an exact allowlist, and global IPs. Rebinding/proxy risks remain; no general Network Plugin ships in
v0.1.

### Filesystem damage

Traversal, absolute paths, symlink escape, writes, and deletion can harm data. Canonical workspace
checks and permission defaults mitigate this; enabled writes still require backups/isolation.

### Supply-chain attack

Dependencies, build tooling, GitHub Actions, Plugins, and Skills can be compromised. The repository
keeps dependencies small, pins CI actions by commit, avoids Plugin auto-discovery, uses manifests,
and requires CI plus human review. Future work includes hashes, SBOM, signatures, and provenance.

### Third-party contribution risk

An unknown PR can modify tests, workflows, permissions, or Plugin code. CI has read-only repository
permissions, does not use `pull_request_target`, and does not receive project secrets. Security-
sensitive contributions receive focused human review and regression tests.

## 8. What Codex Security can help solve

Codex Security can assist reviewers with concrete AgentForge paths:

- trace user/Skill/repository text into Shell argv and subprocess sinks;
- find Filesystem calls that bypass `PathPolicy` or use a validated path incorrectly;
- find direct HTTP/socket calls outside `NetworkPolicy`;
- follow secrets from environment through logs, errors, Plugin results, and LLM prompts;
- generate path-traversal, command-injection, Python-escape, and permission-bypass cases;
- inspect third-party Plugins for import-time side effects and undeclared capabilities;
- review GitHub Actions event choice, token scopes, action pinning, and secret exposure;
- assess dependency/build changes and supply-chain blast radius;
- verify that prompt injection can or cannot cross the final code permission seam.

The key review target is the whole chain:

```text
Untrusted input → LLM decision → Skill → Plugin → Permission → real system capability
```

See [codex-security.md](codex-security.md) for the 12 prioritized attack chains and workflow.

## 9. OpenAI API quota for real maintenance work

OpenAI API usage can support:

- Issue triage, summaries, priority suggestions, missing-information prompts, and duplicate
  candidates;
- PR diff summaries, module/risk analysis, suggested tests, and reviewer context;
- release notes and changelog drafts from actual merged PRs/commits;
- README/code drift checks and Plugin/Skill documentation drafts;
- unit, boundary, regression, and security test suggestions;
- contributor onboarding, good-first-issue context, CI failure explanations, and repository Q&A;
- security report summaries, fix-PR analysis, regression test drafts, and dependency advisory
  explanations.

These are decision-support workflows. Writes, labels, merges, releases, and disclosure remain human
decisions. Inputs should be minimized and redacted, and quota/cost monitored. See
[openai-api-maintenance.md](openai-api-maintenance.md).
