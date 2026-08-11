"""Outbound URL checks for allowlists and common SSRF destinations."""

import ipaddress
import socket
from collections.abc import Collection
from dataclasses import dataclass
from urllib.parse import urlsplit

from agentforge.exceptions import PolicyViolationError


@dataclass(frozen=True, slots=True)
class ValidatedURL:
    """Canonical network destination approved by policy."""

    url: str
    hostname: str
    addresses: tuple[str, ...]


class NetworkPolicy:
    """Require HTTPS, an explicit domain, and globally routable addresses."""

    def __init__(self, allowed_domains: Collection[str]) -> None:
        self._allowed_domains = frozenset(domain.lower().rstrip(".") for domain in allowed_domains)

    def validate_url(self, url: str, *, resolve_dns: bool = True) -> ValidatedURL:
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "https":
            raise PolicyViolationError("Only HTTPS network requests are allowed")
        if parsed.username or parsed.password:
            raise PolicyViolationError("Credentials in request URLs are forbidden")
        if parsed.port not in {None, 443}:
            raise PolicyViolationError("Only the standard HTTPS port is allowed")
        if not parsed.hostname:
            raise PolicyViolationError("A network request must include a hostname")

        hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if not self._is_allowed_domain(hostname):
            raise PolicyViolationError(f"Domain is not allowlisted: {hostname}")
        if hostname == "localhost" or hostname.endswith((".localhost", ".local")):
            raise PolicyViolationError("Localhost destinations are forbidden")

        addresses: tuple[str, ...]
        try:
            literal = ipaddress.ip_address(hostname)
        except ValueError:
            addresses = self._resolve(hostname) if resolve_dns else ()
        else:
            self._require_global(literal)
            addresses = (str(literal),)

        for address in addresses:
            self._require_global(ipaddress.ip_address(address))
        return ValidatedURL(url=url, hostname=hostname, addresses=addresses)

    def _is_allowed_domain(self, hostname: str) -> bool:
        for allowed in self._allowed_domains:
            if allowed.startswith("*.") and hostname.endswith(allowed[1:]):
                return True
            if hostname == allowed:
                return True
        return False

    @staticmethod
    def _resolve(hostname: str) -> tuple[str, ...]:
        try:
            info = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise PolicyViolationError(f"Could not resolve allowlisted domain: {hostname}") from exc
        return tuple(sorted({str(entry[4][0]) for entry in info}))

    @staticmethod
    def _require_global(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
        if not address.is_global:
            raise PolicyViolationError("Private, local, metadata, and reserved IPs are forbidden")
