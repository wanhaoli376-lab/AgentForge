# Security Policy

AgentForge handles untrusted text, model output, local files, subprocesses, third-party code,
and API credentials. Security reports are taken seriously.

## Supported versions

AgentForge is currently pre-1.0. Security fixes are provided on the latest `main` branch and the
latest published release when releases begin. Older alpha snapshots may not receive patches.

## Reporting a vulnerability

Do not open a public Issue for an undisclosed vulnerability or include real credentials in a
report. Use GitHub's private vulnerability reporting channel:

<https://github.com/wanhaoli376-lab/AgentForge/security/advisories/new>

Include:

- affected version or commit;
- operating system and Python version;
- required configuration and permissions;
- a minimal reproduction using fake credentials and disposable data;
- impact, expected boundary, and any suggested mitigation.

The maintainers will acknowledge a complete report when practical, investigate it, and
coordinate disclosure after a fix or mitigation is available. No response-time guarantee is
made during the alpha phase.

## High-value report areas

- workspace escape, path traversal, or symlink bypass;
- command-policy or argv-validation bypass;
- arbitrary code execution without the documented permission;
- secret exposure through logs, tool results, model context, or errors;
- unauthorized network or GitHub writes;
- prompt or Skill injection that reaches a real capability despite policy;
- malicious Plugin loading or dependency/build compromise;
- GitHub Actions behavior that exposes secrets to an untrusted pull request.

## Known security limitations

- `ProcessSandbox` is not kernel, VM, container, seccomp, or job-object isolation.
- The Python AST policy is conservative defense in depth, not a safe-arbitrary-code theorem.
- A third-party Plugin is Python code and can act at import time outside the Plugin interface.
- Enabling test execution can run malicious project code and test hooks.
- DNS allowlist checks do not eliminate every rebinding, proxy, or compromised-DNS scenario.
- Redaction recognizes common formats and explicit runtime values; no redactor can identify every
  possible encoded or transformed secret.

Use a disposable container or VM for untrusted repositories and Plugins. Keep high-risk
permissions disabled unless the task and environment justify them. See
[docs/security-model.md](docs/security-model.md) and [docs/threat-model.md](docs/threat-model.md).
