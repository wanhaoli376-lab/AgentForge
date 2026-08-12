"""Unified LLM seam with Responses and OpenAI-compatible Chat adapters."""

import os
from typing import Literal, Protocol

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

from agentforge.exceptions import LLMError, MissingCredentialError
from agentforge.security.secret_filter import SecretFilter


class LLMRequest(BaseModel):
    """Provider-neutral text generation request."""

    instructions: str = Field(min_length=1)
    input: str = Field(min_length=1)


class LLMClient(Protocol):
    """Seam implemented by hosted providers and deterministic test adapters."""

    def generate(self, request: LLMRequest) -> str:
        """Generate text for one request."""


class _OpenAICompatibleClient:
    """Shared credential, endpoint, and redaction behavior for OpenAI-compatible adapters."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        client: OpenAI | None = None,
        secret_filter: SecretFilter | None = None,
    ) -> None:
        self.model = model
        self._api_key_env = api_key_env
        self._api_key = api_key if api_key is not None else os.getenv(api_key_env)
        self._base_url = base_url
        self._client = client
        self._secret_filter = secret_filter or SecretFilter.from_environment(
            additional_names=(api_key_env,),
        )

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise MissingCredentialError(
                f"{self._api_key_env} is not set. Export it in your environment before running "
                "AgentForge, or choose another api_key_env in the configuration."
            )
        if self._base_url is None:
            self._client = OpenAI(api_key=self._api_key, timeout=60.0, max_retries=2)
        else:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=60.0,
                max_retries=2,
            )
        return self._client

    def _safe_request(self, request: LLMRequest) -> tuple[str, str]:
        return (
            self._secret_filter.redact_text(request.instructions),
            self._secret_filter.redact_text(request.input),
        )

    def _safe_output(self, output: str | None) -> str:
        if output is None or not output.strip():
            raise LLMError("LLM provider returned an empty response")
        return self._secret_filter.redact_text(output)

    @staticmethod
    def _raise_provider_error(exc: OpenAIError) -> None:
        raise LLMError(
            "LLM provider request failed; check connectivity, model access, and quota, and verify "
            "the configured endpoint"
        ) from exc


class OpenAILLMClient(_OpenAICompatibleClient):
    """OpenAI Responses API implementation of the LLM seam."""

    def generate(self, request: LLMRequest) -> str:
        client = self._get_client()
        safe_instructions, safe_input = self._safe_request(request)
        try:
            response = client.responses.create(
                model=self.model,
                instructions=safe_instructions,
                input=safe_input,
                store=False,
            )
        except OpenAIError as exc:
            self._raise_provider_error(exc)
        return self._safe_output(response.output_text)


class OpenAICompatibleChatLLMClient(_OpenAICompatibleClient):
    """Chat Completions adapter for OpenAI-compatible model providers."""

    def generate(self, request: LLMRequest) -> str:
        client = self._get_client()
        safe_instructions, safe_input = self._safe_request(request)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": safe_instructions},
                    {"role": "user", "content": safe_input},
                ],
            )
        except OpenAIError as exc:
            self._raise_provider_error(exc)
        output = response.choices[0].message.content if response.choices else None
        return self._safe_output(output)


def create_llm_client(
    *,
    model: str,
    api_mode: Literal["responses", "chat_completions"] = "responses",
    api_key_env: str = "OPENAI_API_KEY",
    base_url: str | None = None,
    secret_filter: SecretFilter | None = None,
) -> LLMClient:
    """Create the configured provider adapter behind the stable LLMClient seam."""

    adapter = OpenAILLMClient if api_mode == "responses" else OpenAICompatibleChatLLMClient
    return adapter(
        model=model,
        api_key_env=api_key_env,
        base_url=base_url,
        secret_filter=secret_filter,
    )
