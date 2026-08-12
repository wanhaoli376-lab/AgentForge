import os

import pytest

from agentforge.llm.client import LLMRequest, OpenAILLMClient

pytestmark = pytest.mark.skipif(
    os.getenv("AGENTFORGE_LIVE_API") != "1",
    reason="set AGENTFORGE_LIVE_API=1 to allow a billed OpenAI API request",
)


def test_openai_responses_api_round_trip() -> None:
    model = os.getenv("AGENTFORGE_MODEL", "gpt-5.6-luna")
    client = OpenAILLMClient(model=model)

    output = client.generate(
        LLMRequest(
            instructions="Return the exact marker AGENTFORGE_LIVE_OK and nothing else.",
            input="Perform the AgentForge live API health check.",
        )
    )

    assert output.strip() == "AGENTFORGE_LIVE_OK"
