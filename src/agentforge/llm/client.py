"""Unified LLM client with an OpenAI Responses API adapter."""

import os
from typing import Protocol

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


class OpenAILLMClient:
    """OpenAI Responses API implementation of the LLM seam."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        client: OpenAI | None = None,
        secret_filter: SecretFilter | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self._client = client
        self._secret_filter = secret_filter or SecretFilter.from_environment()

    def generate(self, request: LLMRequest) -> str:
        client = self._get_client()
        safe_instructions = self._secret_filter.redact_text(request.instructions)
        safe_input = self._secret_filter.redact_text(request.input)
        try:
            response = client.responses.create(
                model=self.model,
                instructions=safe_instructions,
                input=safe_input,
                store=False,
            )
        except OpenAIError as exc:
            raise LLMError(
                "OpenAI request failed; check connectivity, model access, and quota"
            ) from exc
        output = response.output_text
        if not output.strip():
            raise LLMError("OpenAI returned an empty response")
        return self._secret_filter.redact_text(output)

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise MissingCredentialError(
                "OPENAI_API_KEY is not set. Export it in your environment before running "
                "AgentForge."
            )
        self._client = OpenAI(api_key=self._api_key, timeout=60.0, max_retries=2)
        return self._client
