import logging
from io import StringIO

from agentforge.security.secret_filter import RedactingLogFilter, SecretFilter


def test_common_credentials_are_redacted_before_logging_or_llm_use() -> None:
    secret_filter = SecretFilter(additional_secrets={"custom-secret-value"})
    source = (
        "OPENAI_API_KEY=sk-example-secret-value "
        "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456 "
        "Authorization: Bearer header.payload.signature "
        "custom-secret-value"
    )

    redacted = secret_filter.redact_text(source)

    assert "sk-example-secret-value" not in redacted
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "header.payload.signature" not in redacted
    assert "custom-secret-value" not in redacted
    assert redacted.count("[REDACTED]") >= 4


def test_logging_filter_redacts_lazy_format_arguments() -> None:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.addFilter(RedactingLogFilter(SecretFilter()))
    logger = logging.getLogger("agentforge.tests.redaction")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("OPENAI_API_KEY=%s", "sk-example-secret")

    assert "sk-example-secret" not in output.getvalue()
    assert "[REDACTED]" in output.getvalue()


def test_custom_provider_key_is_loaded_for_redaction_by_environment_name() -> None:
    custom_key = "provider-secret-without-a-known-token-prefix"
    secret_filter = SecretFilter.from_environment(
        {"CUSTOM_LLM_API_KEY": custom_key},
        additional_names=("CUSTOM_LLM_API_KEY",),
    )

    assert secret_filter.redact_text(f"credential={custom_key}") == "credential=[REDACTED]"
