# Architecture

AgentForge separates model reasoning from real capabilities. The model receives descriptions and
structured results; it never receives a Python object that directly opens files, starts processes,
or calls GitHub.

## Runtime flow

```text
Natural-language task
        │
        ▼
Skill catalog ──► LLM Skill selection
        │
        ▼
Selected untrusted Skill instructions
        │
        ▼
LLM execution plan (JSON)
        │
        ▼
Plan schema + Plugin/action validation
        │
        ▼
Per-action permission check
        │
        ▼
Plugin policy and adapter
        │
        ├── Filesystem → PathPolicy → workspace
        ├── Shell → CommandPolicy → ProcessSandbox
        ├── Python → PythonCodePolicy → ProcessSandbox
        └── GitHub → NetworkPolicy → GET-only API client
        │
        ▼
Structured, redacted tool results
        │
        ▼
LLM final synthesis
```

The LLM can propose `filesystem.read("../../secret")`; `PathPolicy` still rejects it. This is the
central architectural rule: model output is untrusted data until code validates and authorizes it.

## Modules

### `agent`

- `core.py` owns the public `Agent.run(task) -> AgentResult` interface.
- `planner.py` performs Skill selection, parses model JSON, bounds plan length, and rejects unknown
  Plugin actions.
- `executor.py` dispatches registered Plugins, stops at the first failed action, and redacts results
  before model reuse.
- `context.py` defines plans, steps, execution records, and public results.

### `skills`

- `validator.py` safely parses size-limited `SKILL.md` files with strict YAML metadata.
- `loader.py` scans one explicit root and rejects symlink escapes and duplicate names.
- `registry.py` provides keyword candidates, Plugin-dependency validation, and untrusted prompt
  markers.

Skills are data. They can recommend an action but cannot add a permission or register a Plugin.

### `plugins`

`Plugin.execute(action, arguments, context)` is the common interface. The base implementation:

1. rejects unknown actions;
2. checks the action's permissions;
3. validates arguments with the declared Pydantic model;
4. calls the Plugin implementation;
5. returns a stable `PluginResult` envelope.

The registry is instance-local; there is no import-time global registry. v0.1 supports explicit
registration. Automatic package discovery is planned because safe provenance and review need to
be designed before convenience loading.

### `security`

- `permissions.py`: authoritative capability grants.
- `path_policy.py`: canonical path resolution and sensitive-path denial.
- `command_policy.py`: executable/action allowlists and injection syntax denial.
- `python_policy.py`: conservative AST checks for the experimental Python Plugin.
- `network_policy.py`: HTTPS/domain/IP destination validation.
- `sandbox.py`: child process, filtered environment, no stdin, timeout, bounded output.
- `secret_filter.py`: recursive and logging redaction.

### `llm`

`LLMClient.generate(LLMRequest) -> str` is the provider seam. `OpenAILLMClient` uses the Responses
API, while `OpenAICompatibleChatLLMClient` adapts OpenAI-compatible Chat Completions providers.
Runtime configuration chooses the adapter, model, compatible base URL, and credential environment
variable without exposing those differences to the Agent Core. Both adapters use the OpenAI SDK.
Planner and Agent modules depend on the seam, so tests use deterministic adapters.

### `config` and `runtime`

Pydantic config models reject unknown keys. `runtime.py` constructs registries, permissions,
Plugins, and the LLM client. All built-in Plugins remain registered for inspection. The planner
receives only actions covered by the current grants, together with their argument JSON Schemas.
Registration and discovery do not grant capability: every action is still independently checked
by the permission manager before execution.

## Execution semantics

- A plan contains at most the configured `max_tool_rounds` and never more than the model schema's
  hard maximum.
- Steps run sequentially and stop at the first failed action. Remaining steps are not executed;
  completed actions are neither rolled back nor automatically replayed. There is no multi-agent,
  parallel executor, or automatic replanning in v0.1.
- Shell and Python return `ok=false` with `process_failed` for nonzero exits or `process_timeout`
  for timeouts. Exit code, stdout, stderr, truncation and timing stay in `data` even on failure.
- `AgentResult.ok` is true only when all planned actions and final synthesis succeed. Blocked or
  failed actions produce `tool_execution_failed`; the CLI exits with code 2 while retaining any
  useful final explanation. Inspect `tool_results` to distinguish failures from steps never run.
- If final synthesis fails, `AgentResult` retains the selected Skills, plan and completed tool
  records with the LLM error. Inspect these records before retrying a task with side effects.
- `run --json` emits the full structured result on success or failure. Human-readable output and
  interactive mode display partial answers and the completed-action count on errors.
- Tool output is size-limited and secret-filtered before returning to the LLM. The planner also
  filters requests and responses for custom LLM adapters, and public Agent errors are redacted.

## Deliberate omissions

v0.1 does not implement a general network Plugin, dynamic Plugin installation, container
orchestration, background jobs, multi-agent delegation, GitHub writes, a vector database, or a
web UI. Interfaces leave room for those additions, but documentation must not describe them as
current behavior.
