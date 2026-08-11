---
name: test-runner
version: 0.1.0
description: Run project tests through the restricted shell and explain failures.
author: AgentForge contributors
required_plugins:
  - filesystem
  - shell
keywords:
  - test
  - tests
  - pytest
  - failure
---
# Test Runner

1. Inspect project metadata to identify the test framework.
2. Prefer the narrowest relevant test command before the full suite.
3. Use only commands permitted by the Shell Plugin and current configuration.
4. Summarize the first actionable failure, likely cause, and affected behavior.
5. Never weaken tests, disable security policy, or read outside the workspace.

Shell execution requires an explicit `shell_execute` grant. This Skill cannot grant it.
