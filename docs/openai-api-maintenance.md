# OpenAI API for Open-Source Maintenance

AgentForge centralizes model access behind `LLMClient`. The default adapter uses the
[OpenAI Responses API](https://developers.openai.com/api/docs/guides/function-calling) and reads
`OPENAI_API_KEY` from the environment. An OpenAI-compatible Chat Completions adapter is also
available through configuration. API output is advisory: maintainers review suggestions before
labels, comments, merges, releases, or security disclosure.

## Issue triage

The `github-maintainer` Skill can fetch bounded Issue data and ask the model to produce:

- a concise problem summary;
- category: bug, feature, question, documentation, security, or duplicate candidate;
- priority suggestion with reasoning;
- likely duplicate search terms or candidates;
- missing environment, version, reproduction, expected behavior, or logs;
- a draft maintainer reply.

v0.1 does not auto-label or close Issues. Security-looking Issues should be moved to a private
reporting path by a human rather than summarized publicly with exploit details.

## Pull request review

Given PR metadata, file changes, and a bounded diff, the API can help:

- explain the main behavior change and affected modules;
- identify permission, path, process, network, credential, or CI-sensitive code;
- suggest focused and regression tests;
- list assumptions a reviewer should verify;
- summarize a large PR for a domain reviewer;
- draft review questions without posting them.

The model must not be the only reviewer for third-party Plugins, dependency changes, workflow
changes, authentication, or remote writes.

## Duplicate Issue detection

Issue titles and summaries can be compared to a supplied candidate set. The output should be a
ranked “duplicate candidate” list with shared symptoms and important differences—not an automatic
closure decision. Semantic retrieval is planned; v0.1 supplies candidates through GitHub reads.

## Release notes and changelog

For reviewed PRs or commits, the model can group evidence into:

- Features
- Bug Fixes
- Security
- Documentation
- Breaking Changes

It can also draft upgrade notes and a changelog entry. Inputs must be the actual merged range, and
the prompt must forbid invented changes. A maintainer verifies issue links, breaking status, and
security disclosure timing.

## Documentation maintenance

The API can compare a bounded repository structure and docs to:

- flag README commands or module lists that appear stale;
- draft documentation for a new Plugin action or config field;
- generate usage examples from public interfaces;
- identify a new Plugin without permission/security documentation;
- identify a new Skill without metadata or usage guidance;
- answer repository questions for contributors.

Generated documentation is checked against code and tests before merge.

## Tests

The model can suggest unit, boundary, regression, and security cases, especially around malformed
plan JSON, path syntax, command flags, token formats, redirects, response limits, and permission
ordering. Tests should assert behavior through public interfaces and be executed locally/CI before
acceptance.

## Contributor support

Repository Q&A can explain architecture, locate the right module, suggest a good-first-issue
candidate, summarize contribution rules, and translate a CI failure into a focused next action.
Answers should link to canonical docs and avoid promising maintainers will accept a design.

## Security maintenance

With appropriately redacted inputs, the API can:

- summarize a private report for authorized reviewers;
- trace untrusted-input-to-capability paths;
- explain a security fix PR and residual risk;
- propose a minimal regression test;
- summarize a dependency advisory and affected module;
- draft a disclosure, upgrade note, or backport checklist.

Do not send live credentials, private customer data, undisclosed exploit details beyond the
authorized workflow, or entire repositories unnecessarily.

## Operating controls

- use least-privilege OpenAI project keys and spend/rate limits;
- keep keys in environment/secret managers, never repo config;
- bound Issue, diff, file, and command output before model input;
- redact known secrets before every request and log;
- record what evidence a generated conclusion used;
- cache or batch only when confidentiality and staleness are acceptable;
- require human approval for external writes and releases;
- monitor cost, latency, errors, and model/version changes.

Useful API quota is therefore not consumed only by end-user chat. It can fund repeatable
maintenance work: triage, review context, release notes, docs, tests, contributor support,
security analysis, changelog generation, and repository Q&A.
