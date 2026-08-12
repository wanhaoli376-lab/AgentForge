import socket

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


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("https://user:password@api.github.com/repos", "Credentials"),
        ("https://api.github.com:8443/repos", "standard HTTPS port"),
        ("https:///repos", "include a hostname"),
        ("https://example.com/repos", "not allowlisted"),
        ("https://service.local/repos", "Localhost destinations"),
    ],
)
def test_network_policy_rejects_ambiguous_or_unapproved_destinations(
    url: str,
    message: str,
) -> None:
    policy = NetworkPolicy(allowed_domains={"api.github.com", "service.local"})

    with pytest.raises(PolicyViolationError, match=message):
        policy.validate_url(url, resolve_dns=False)


def test_wildcard_allowlist_accepts_subdomains_but_not_the_parent_domain() -> None:
    policy = NetworkPolicy(allowed_domains={"*.example.com"})

    accepted = policy.validate_url("https://api.example.com/data", resolve_dns=False)

    assert accepted.hostname == "api.example.com"
    with pytest.raises(PolicyViolationError, match="not allowlisted"):
        policy.validate_url("https://example.com/data", resolve_dns=False)


def test_network_policy_returns_sorted_unique_dns_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def resolve(*_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.4.4", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.4.4", 443)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    result = NetworkPolicy({"dns.example"}).validate_url("https://dns.example/data")

    assert result.addresses == ("8.8.4.4", "8.8.8.8")


def test_network_policy_converts_dns_failures_to_a_policy_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> list[tuple[object, ...]]:
        raise OSError("resolver details")

    monkeypatch.setattr(socket, "getaddrinfo", fail)

    with pytest.raises(PolicyViolationError, match="Could not resolve allowlisted domain"):
        NetworkPolicy({"dns.example"}).validate_url("https://dns.example/data")


def test_allowlisted_public_ip_literal_is_accepted() -> None:
    result = NetworkPolicy({"8.8.8.8"}).validate_url("https://8.8.8.8/dns-query")

    assert result.addresses == ("8.8.8.8",)
