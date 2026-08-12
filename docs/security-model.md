# Security Model

AgentForge is secure-by-default at the framework layer: dangerous permissions start disabled,
model output is untrusted, and code—not a prompt—makes the final authorization decision. This
model reduces common agent risks; it does not make arbitrary code or third-party Python safe.

## Security goals

- Prevent model, user, Skill, and repository text from directly invoking system capabilities.
- Confine framework-mediated file operations to one workspace.
- Require explicit permissions for writes, deletion, subprocesses, Python, network, and GitHub.
- Reject shell syntax and run subprocesses with argv and `shell=False`.
- Keep common credential values out of logs and LLM-bound tool results.
- Restrict GitHub v0.1 behavior to reads and local draft construction.
- Keep failures structured so a blocked operation is visible rather than silently retried.

## Non-goals and limitations

- Complete OS/container/VM isolation.
- Safe execution of arbitrary Python or arbitrary repository tests.
- Automatic trust of third-party Plugins because they declare permissions.
- Detection of every encoded, split, transformed, or novel secret format.
- Elimination of every DNS rebinding, proxy, dependency, or compromised-runner risk.
- Protection from an administrator who intentionally changes trusted config or framework code.

## Trust boundaries

| Input or module | Trust level | Treatment |
| --- | --- | --- |
| User task | Untrusted | Redacted, supplied as model data, never executed directly |
| LLM response | Untrusted | Parsed into strict Skill-selection/plan models |
| Skill Markdown | Untrusted | Size/schema checked and marked as untrusted prompt content |
| Repository/Issue/PR content | Untrusted | Bounded tool data; cannot authorize another action |
| Plugin implementation | Privileged code | Explicitly registered and human-reviewed; metadata is not containment |
| Config file | Trusted operator input | Strict schema; controls grants and limits |
| Permission/policy code | Trusted computing base | Makes final allow/deny decision |
| OS, Python runtime, dependencies | Trusted platform | Must be patched and sourced carefully |

The critical chain is:

```text
Untrusted input → LLM decision → Skill → Plugin request → permission/policy → real capability
```

Security review must trace the full chain. Finding a safe prompt is insufficient if an action can
bypass policy; finding a dangerous function is insufficient if no untrusted path can reach it.

## Default permissions

| Permission | Default | Rationale |
| --- | --- | --- |
| Filesystem read | On, workspace only | Enables repository understanding |
| Filesystem write/delete | Off | Prevents accidental or injected damage |
| Shell execute | Off | Tests and commands execute repository code |
| Python execute | Off | AST checks are not OS isolation |
| General network | Off | No general Network Plugin exists in v0.1 |
| GitHub read | On | Supports public maintenance workflows through a fixed API adapter |
| GitHub write | Off | v0.1 implements no remote write action |

Registration and permission are separate. The planner may see a disabled action so it can produce
a transparent blocked result, but the base Plugin interface checks the grant before implementation.

## Filesystem controls

`PathPolicy` rejects absolute paths, `..`, home notation, sensitive directories, selected secret
filenames, and paths whose canonical resolution leaves the workspace. It calls `resolve()` before
use, so a supported symlink cannot point outside and remain accepted. The Filesystem Plugin does
not recursively delete directories.

Residual risks include filesystem races after validation, platform-specific link types, hard links
to sensitive content, and sensitive data stored under an ordinary filename. Run untrusted work in
a disposable environment and use OS permissions as another layer.

## Shell controls

The Shell Plugin accepts only an argv array. `CommandPolicy`:

- hard-denies shell interpreters and destructive/download commands;
- permits configured `git`, `pytest`, and `python` adapters by default;
- limits Git to `status`, `diff`, `log`, and `show`;
- denies metacharacters, executable paths, POSIX/Windows absolute or traversal arguments, Git
  write/output flags, `diff --no-index`, and Python `-c`, `-m`, and stdin execution;
- maps Python and pytest to the current trusted interpreter.

`ProcessSandbox` uses `shell=False`, closes stdin, fixes `cwd`, filters environment names, disables
Git prompting/global config, limits observable output, redacts it, and kills the direct child on
timeout. It does not reliably kill every descendant on every OS or constrain CPU, memory, disk,
syscalls, child networking, or child filesystem access. A future container/OS adapter belongs
behind the same process interface.

## Python controls

The experimental Python Plugin parses an AST, allowlists selected data-oriented standard-library
imports, and blocks direct I/O, dynamic execution, introspection calls, private/dunder attributes,
and relative imports. It starts `python -I -S` in a separate bounded child.

This is defense in depth, not a proof that Python is safely sandboxed. Do not enable
`python_execute` for an adversary. Prefer a container or VM for untrusted generated code.

## Network and GitHub controls

`NetworkPolicy` requires HTTPS, an explicit allowlisted domain, standard port 443, no URL
credentials, and globally routable resolved IPs. It denies localhost, private, link-local,
reserved, multicast, unspecified, and cloud-metadata destinations.

The GitHub client uses a fixed configured API origin, no redirect following, GET only, timeout,
bounded response streaming, safe status errors, and optional `GITHUB_TOKEN`. Issue drafts are local
data with `submitted: false`. General network access is not implemented.

## Prompt injection

Prompt injection is expected, not exceptional. A malicious Skill, README, Issue, PR patch, or tool
result may ask the model to ignore rules, reveal a token, or call a dangerous action. Controls are:

1. higher-priority prompt language labels those sources as data;
2. LLM output must parse into known Plugin/action models;
3. action-level permissions run before implementation;
4. Plugin-specific path, command, Python, or network policy runs in code;
5. structured failure returns to the model;
6. security tests demonstrate that an injected Skill cannot read outside the workspace.

Prompt wording can reduce mistakes. Only steps 2–4 enforce the boundary.

## Credentials and logging

The configured LLM credential and `GITHUB_TOKEN` come from environment variables. Config accepts
only the LLM credential's environment variable name, never its value. `SecretFilter` recognizes
common OpenAI/GitHub/Bearer/AWS formats plus the exact selected provider credential at runtime. A
logging filter formats then redacts lazy arguments before handlers emit the record. The executor
recursively redacts tool results before final LLM synthesis.

A custom LLM endpoint receives task text, selected Skill instructions, plans, and bounded tool
summaries. Treat the endpoint as a trusted data processor. Remote endpoints must use HTTPS and URL
credentials are rejected, but transport validation cannot establish a provider's privacy policy.

Do not place credentials in repository files. Redaction is a last line of defense, not a storage
strategy.

## Third-party Plugins and Skills

- Skills are parsed data and cannot execute during loading.
- Plugins are Python and can execute during import or construction.
- v0.1 has no automatic Plugin discovery or installation.
- Community Plugins require manifests, tests, CI, security review, and human code review.
- Unknown pull requests must not receive secrets or high-privilege workflow triggers.

For hostile Plugins or repositories, use a disposable container/VM with no host credentials,
minimal mounts, egress filtering, and a short-lived token scoped to read-only operations.

## Release integrity

PyPI publishing uses a dedicated GitHub Release workflow and Trusted Publishing rather than a
stored API token. The workflow verifies that the release tag matches package metadata and belongs
to `main`, separates the read-only build job from the OIDC-enabled publish job, pins third-party
Actions to full commit SHAs, checks both distributions, smoke-tests the wheel, and requests a PEP
740 attestation. The `pypi` environment is the maintainer approval boundary.

The workflow cannot prove that source code or a dependency is benign. Treat changes to the release
workflow, package metadata, GitHub environment, PyPI publisher, and maintainer access as
credential-equivalent security changes.
