import pytest

from agentforge.exceptions import PolicyViolationError
from agentforge.security.network_policy import NetworkPolicy


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/admin",
        "https://localhost/admin",
        "https://169.254.169.254/latest/meta-data",
        "http://api.github.com/repos/openai/openai-python",
    ],
)
def test_private_metadata_localhost_and_plain_http_are_rejected(url: str) -> None:
    policy = NetworkPolicy(
        allowed_domains={"127.0.0.1", "localhost", "169.254.169.254", "api.github.com"}
    )

    with pytest.raises(PolicyViolationError):
        policy.validate_url(url, resolve_dns=False)


def test_exact_allowlisted_https_domain_is_accepted_without_credentials() -> None:
    policy = NetworkPolicy(allowed_domains={"api.github.com"})

    result = policy.validate_url(
        "https://api.github.com/repos/openai/openai-python",
        resolve_dns=False,
    )

    assert result.hostname == "api.github.com"
