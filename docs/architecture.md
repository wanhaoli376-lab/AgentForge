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
- `executor.py` dispatches only registered Plugins and redacts results before model reuse.
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
Plugins, and the LLM client. Registration does not grant capability: all built-in Plugins are
present so the planner understands the interface, while action calls still fail unless the
permission manager grants them.

## Execution semantics

- A plan contains at most the configured `max_tool_rounds` and never more than the model schema's
  hard maximum.
- Steps run sequentially in v0.1. There is no multi-agent or parallel tool executor.
- A Plugin operation can succeed while the underlying command exits non-zero; command status is
  preserved in structured data for final explanation.
- A blocked Plugin call is also a structured result. The final model must disclose that it was
  blocked rather than pretending it ran.
- Tool output is size-limited and secret-filtered before returning to the LLM.

## Deliberate omissions

v0.1 does not implement a general network Plugin, dynamic Plugin installation, container
orchestration, background jobs, multi-agent delegation, GitHub writes, a vector database, or a
web UI. Interfaces leave room for those additions, but documentation must not describe them as
current behavior.
