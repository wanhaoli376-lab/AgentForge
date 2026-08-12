from collections import deque
from pathlib import Path
from typing import Any

import pytest

from agentforge.config.models import AgentConfig, AppConfig, WorkspaceConfig
from agentforge.llm.client import LLMRequest
from agentforge.runtime import build_runtime
from agentforge.security.secret_filter import SecretFilter


class ScriptedLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = deque(responses)

    def generate(self, _request: LLMRequest) -> str:
        return self._responses.popleft()


def test_runtime_wires_custom_provider_configuration_and_secret_redaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_key = "custom-provider-key-without-a-known-prefix"
    monkeypatch.setenv("CUSTOM_LLM_API_KEY", custom_key)
    captured: dict[str, Any] = {}

    def create_client(**kwargs: Any) -> ScriptedLLM:
        captured.update(kwargs)
        return ScriptedLLM(
            [
                '{"skills": []}',
                '{"rationale": "No tools needed", "steps": []}',
                "Custom provider answer.",
            ]
        )

    monkeypatch.setattr("agentforge.runtime.create_llm_client", create_client)
    config = AppConfig(
        agent=AgentConfig(
            model="provider-model",
            api_mode="chat_completions",
            base_url="https://provider.example/v1",
            api_key_env="CUSTOM_LLM_API_KEY",
        ),
        workspace=WorkspaceConfig(root=tmp_path),
    )

    runtime = build_runtime(config)
    result = runtime.agent.run("answer without tools")

    assert result.answer == "Custom provider answer."
    assert captured["model"] == "provider-model"
    assert captured["api_mode"] == "chat_completions"
    assert captured["base_url"] == "https://provider.example/v1"
    assert captured["api_key_env"] == "CUSTOM_LLM_API_KEY"
    secret_filter = captured["secret_filter"]
    assert isinstance(secret_filter, SecretFilter)
    assert custom_key not in secret_filter.redact_text(custom_key)
