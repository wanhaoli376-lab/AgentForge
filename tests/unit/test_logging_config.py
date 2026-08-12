import logging
from io import StringIO

from agentforge.logging_config import configure_logging


def test_logging_redacts_the_selected_provider_credential() -> None:
    custom_key = "custom-provider-key-without-a-known-prefix"
    output = StringIO()
    logger = configure_logging(
        stream=output,
        environ={"CUSTOM_LLM_API_KEY": custom_key},
        additional_secret_names=("CUSTOM_LLM_API_KEY",),
    )

    logger.info("provider credential=%s", custom_key)

    assert custom_key not in output.getvalue()
    assert "provider credential=[REDACTED]" in output.getvalue()
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
