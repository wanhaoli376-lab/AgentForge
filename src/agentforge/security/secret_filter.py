"""Best-effort credential redaction for logs, tool results, and LLM context."""

import logging
import os
import re
from collections.abc import Mapping
from typing import Any


class SecretFilter:
    """Redact common token formats plus explicit runtime secret values."""

    _ENV_PATTERN = re.compile(
        r"\b(OPENAI_API_KEY|GITHUB_TOKEN|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)"
        r"\s*[:=]\s*([^\s,'\"}]+)",
        re.IGNORECASE,
    )
    _TOKEN_PATTERNS = (
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_-]{12,}"),
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    )

    def __init__(self, additional_secrets: set[str] | frozenset[str] | None = None) -> None:
        self._additional_secrets = tuple(
            sorted(
                (secret for secret in (additional_secrets or set()) if secret),
                key=len,
                reverse=True,
            )
        )

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "SecretFilter":
        """Include known credential values without retaining the full environment."""

        source = environ if environ is not None else os.environ
        names = (
            "OPENAI_API_KEY",
            "GITHUB_TOKEN",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
        )
        return cls({source[name] for name in names if source.get(name)})

    def redact_text(self, text: str) -> str:
        """Return text with recognized credential material removed."""

        value = self._ENV_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
        for pattern in self._TOKEN_PATTERNS:
            if pattern.pattern.lower().startswith(r"\bbearer"):
                value = pattern.sub("Bearer [REDACTED]", value)
            else:
                value = pattern.sub("[REDACTED]", value)
        for secret in self._additional_secrets:
            value = value.replace(secret, "[REDACTED]")
        return value

    def redact(self, value: Any) -> Any:
        """Recursively redact data before it crosses a trust boundary."""

        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, Mapping):
            return {key: self.redact(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        return value


class RedactingLogFilter(logging.Filter):
    """Apply a SecretFilter before a record is formatted by any handler."""

    def __init__(self, secret_filter: SecretFilter) -> None:
        super().__init__()
        self._secret_filter = secret_filter

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        record.msg = self._secret_filter.redact_text(rendered)
        record.args = ()
        return True
