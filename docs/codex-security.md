# Codex Security and AgentForge

[Codex Security](https://developers.openai.com/codex/security) can be used as an additional review
and investigation layer for AgentForge. It does not replace tests, human review, OS controls, or
the permission layer. The useful question is not merely “does this file call a dangerous
function?” but “can untrusted data reach a real capability without the intended checks?”

## Priority attack chains

1. **User input → Agent → Plugin → Shell.** Trace whether task text can become an executable,
   subcommand, flag, cwd, or argument after `CommandPolicy`; look for alternate subprocess paths,
   `shell=True`, quoting assumptions, and command-specific escape flags.
2. **Skill → Agent → Filesystem.** Verify every file action reaches `PathPolicy`, including create,
   write, delete, directory listing, symlinks, missing targets, and platform-specific paths.
3. **Plugin → unauthorized network.** Find direct `httpx`, socket, SDK, redirect, webhook, or DNS
   use that bypasses `NetworkPolicy` or the declared permission.
4. **Secret/API key leakage.** Follow environment values through logging, exceptions, Plugin
   results, model prompts, HTTP errors, tests, snapshots, and CLI JSON output.
5. **Path traversal.** Generate variants using absolute paths, mixed separators, encoded
   segments, Windows drives/UNC paths, symlinks, junctions, and resolve/use races.
6. **Unsafe subprocess use.** Check argv provenance, executable resolution, cwd, stdin,
   environment, timeout, output draining, descendants, and dangerous Git/pytest/Python flags.
7. **Unsafe dynamic execution.** Review `exec`, `eval`, `compile`, imports, reflection, deserialization,
   and ways to bypass `PythonCodePolicy`; confirm code runs outside the Agent process.
8. **Malicious third-party Plugin behavior.** Identify import/constructor side effects, environment
   access, undeclared capabilities, hidden network calls, install hooks, and dependency additions.
9. **GitHub Actions security.** Review token permissions, event choice, checkout credentials,
   untrusted PR code, action pinning, caches, artifacts, release jobs, and secret availability.
10. **Dependency/supply-chain risk.** Examine new packages, version ranges, build backends,
    maintainers, transitive install scripts, release provenance, and typosquatting.
11. **Permission-check bypass.** Find direct `_execute` calls, Plugin overrides, alternate registries,
    context construction, unsafe defaults, and actions whose declared permission is too broad or
    absent.
12. **Prompt injection reaching tool execution.** Start with malicious Skill/repository/GitHub text,
    inspect the resulting plan, and verify that schemas, permissions, and policies still prevent
    the real side effect.

## Suggested review workflow

1. Start with [the threat model](threat-model.md) and choose one capability chain.
2. Mark the untrusted source, transformation points, authorization check, adapter, and sink.
3. Ask Codex Security to look for a second route to the same sink rather than reviewing one file in
   isolation.
4. Turn each confirmed path into a minimal public-interface regression test under
   `tests/security/`.
5. Review the fix for new bypasses and update the threat model's residual risk.

High-value regression assertions include “the external adapter was never called,” “the secret is
absent from both log message and lazy args,” and “canonical target remains under workspace.”

## What Codex Security cannot establish alone

Static or agent-assisted review cannot prove arbitrary Python safe, guarantee runtime DNS behavior,
validate every dependency publisher, or substitute for a disposable host boundary. Treat findings
as evidence for remediation and tests, not a certificate that AgentForge is completely secure.
