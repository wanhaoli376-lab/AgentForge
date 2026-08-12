# LLM Provider Configuration

AgentForge keeps the Agent Core behind one `LLMClient` interface while allowing two wire protocols:

- `responses`: the OpenAI Responses API and compatible implementations;
- `chat_completions`: OpenAI-compatible Chat Completions providers.

The provider is selected in the `agent` configuration. Credentials are never accepted as config
values; `api_key_env` names the environment variable that contains the key.

## Default OpenAI configuration

```yaml
agent:
  model: gpt-5.6-luna
  api_mode: responses
  api_key_env: OPENAI_API_KEY
```

```bash
export OPENAI_API_KEY="your-project-key"
agentforge --config agentforge.yaml doctor
```

Omit `base_url` to use the OpenAI SDK default endpoint.

## OpenAI-compatible provider

Use a provider's documented model ID and OpenAI-compatible base URL:

```yaml
agent:
  model: provider-model
  api_mode: chat_completions
  base_url: https://provider.example/v1
  api_key_env: MY_LLM_API_KEY
```

```bash
export MY_LLM_API_KEY="your-provider-key"
agentforge --config agentforge.yaml doctor
agentforge --config agentforge.yaml run "Summarize this repository"
```

Choose `responses` only when the provider implements the Responses API. Many compatible providers
implement only Chat Completions, in which case use `chat_completions`.

## Endpoint and credential safety

- Remote `base_url` values must use HTTPS. Plain HTTP is accepted only for loopback hosts such as
  `localhost` and `127.0.0.1`.
- Usernames, passwords, query strings, and fragments are rejected in `base_url`.
- Put only the environment variable name in `api_key_env`; never add an `api_key` field or real
  credential to YAML/TOML.
- AgentForge includes the selected environment variable's value in its best-effort secret filter.
- `agentforge doctor` reports the selected model, protocol, endpoint, and whether the named key is
  present, but never prints the value.
- The selected provider receives task text, Skill instructions, plans, and bounded tool summaries;
  use only an endpoint you trust to process that data.

This configuration supports OpenAI-compatible request formats. A provider with a proprietary,
non-compatible API still needs a separate `LLMClient` adapter.
