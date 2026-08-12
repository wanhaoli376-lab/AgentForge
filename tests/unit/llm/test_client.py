from types import SimpleNamespace
from typing import Any

import pytest
from openai import OpenAIError

from agentforge.exceptions import LLMError, MissingCredentialError
from agentforge.llm.client import (
    LLMRequest,
    OpenAICompatibleChatLLMClient,
    OpenAILLMClient,
)
from agentforge.security.secret_filter import SecretFilter


class FakeResponses:
    def __init__(self, *, output_text: str = "", error: Exception | None = None) -> None:
        self.output_text = output_text
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAI:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


class FakeChatCompletions:
    def __init__(self, *, content: str | None) -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeChatOpenAI:
    def __init__(self, completions: FakeChatCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


def test_openai_client_reports_missing_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAILLMClient(model="gpt-5.6-luna")

    with pytest.raises(MissingCredentialError, match="OPENAI_API_KEY is not set"):
        client.generate(LLMRequest(instructions="Return a greeting.", input="Hello"))


def test_openai_client_redacts_requests_and_responses() -> None:
    secret = "sk-explicit-secret-value"  # noqa: S105 - fake redaction fixture
    responses = FakeResponses(output_text=f"Safe answer, not {secret}")
    client = OpenAILLMClient(
        model="gpt-test",
        api_key="unused-test-key",
        client=FakeOpenAI(responses),  # type: ignore[arg-type]
        secret_filter=SecretFilter({secret}),
    )

    output = client.generate(
        LLMRequest(
            instructions=f"Never reveal {secret}",
            input=f"Summarize {secret}",
        )
    )

    assert output == "Safe answer, not [REDACTED]"
    assert responses.calls == [
        {
            "model": "gpt-test",
            "instructions": "Never reveal [REDACTED]",
            "input": "Summarize [REDACTED]",
            "store": False,
        }
    ]


def test_openai_client_rejects_an_empty_provider_response() -> None:
    client = OpenAILLMClient(
        model="gpt-test",
        client=FakeOpenAI(FakeResponses(output_text="  \n")),  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="empty response"):
        client.generate(LLMRequest(instructions="Answer.", input="Question"))


def test_openai_client_converts_sdk_errors_to_a_safe_domain_error() -> None:
    provider_error = OpenAIError("provider details that must stay internal")
    client = OpenAILLMClient(
        model="gpt-test",
        client=FakeOpenAI(FakeResponses(error=provider_error)),  # type: ignore[arg-type]
    )

    with pytest.raises(LLMError, match="check connectivity, model access, and quota") as caught:
        client.generate(LLMRequest(instructions="Answer.", input="Question"))

    assert "provider details" not in str(caught.value)


def test_openai_client_constructs_the_sdk_adapter_lazily(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = FakeResponses(output_text="Hello")
    fake_client = FakeOpenAI(responses)
    calls: list[dict[str, Any]] = []

    def create_client(**kwargs: Any) -> FakeOpenAI:
        calls.append(kwargs)
        return fake_client

    monkeypatch.setattr("agentforge.llm.client.OpenAI", create_client)
    client = OpenAILLMClient(model="gpt-test", api_key="sk-test-api-key")

    assert client.generate(LLMRequest(instructions="Greet.", input="Hello")) == "Hello"
    assert calls == [{"api_key": "sk-test-api-key", "timeout": 60.0, "max_retries": 2}]


def test_compatible_chat_client_uses_system_and_user_messages() -> None:
    completions = FakeChatCompletions(content="Compatible answer")
    client = OpenAICompatibleChatLLMClient(
        model="qwen-plus",
        api_key="custom-test-key",
        client=FakeChatOpenAI(completions),  # type: ignore[arg-type]
    )

    output = client.generate(LLMRequest(instructions="Be concise.", input="Hello"))

    assert output == "Compatible answer"
    assert completions.calls == [
        {
            "model": "qwen-plus",
            "messages": [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
            ],
        }
    ]


def test_compatible_chat_client_reads_a_custom_key_and_uses_a_custom_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUSTOM_LLM_API_KEY", "custom-provider-key")
    completions = FakeChatCompletions(content="Custom endpoint answer")
    fake_client = FakeChatOpenAI(completions)
    calls: list[dict[str, Any]] = []

    def create_client(**kwargs: Any) -> FakeChatOpenAI:
        calls.append(kwargs)
        return fake_client

    monkeypatch.setattr("agentforge.llm.client.OpenAI", create_client)
    client = OpenAICompatibleChatLLMClient(
        model="provider-model",
        api_key_env="CUSTOM_LLM_API_KEY",
        base_url="https://provider.example/v1",
    )

    output = client.generate(LLMRequest(instructions="Answer.", input="Hello"))

    assert output == "Custom endpoint answer"
    assert calls == [
        {
            "api_key": "custom-provider-key",
            "base_url": "https://provider.example/v1",
            "timeout": 60.0,
            "max_retries": 2,
        }
    ]
