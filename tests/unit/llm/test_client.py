import pytest

from agentforge.exceptions import MissingCredentialError
from agentforge.llm.client import LLMRequest, OpenAILLMClient


def test_openai_client_reports_missing_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAILLMClient(model="gpt-5.6-luna")

    with pytest.raises(MissingCredentialError, match="OPENAI_API_KEY is not set"):
        client.generate(LLMRequest(instructions="Return a greeting.", input="Hello"))
