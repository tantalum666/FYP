"""Explicit browser-only proxy compatibility; never changes provider/OS routing.

Public DNS checks and Playwright routing are defense in depth, not an OS network
sandbox. With an operator-selected local proxy, preflight its public destinations
using bounded HTTPS DNS rather than treating the proxy's fake-IP range as public.
"""

import ipaddress
import json
from urllib.parse import urlsplit

import httpx

from .browser_policy import require_public_dns
from .store import DomainError


def local_browser_proxy(value):
    if not value:
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.username
            or parsed.password
            or not parsed.port
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Use an explicit local HTTP browser proxy") from None
    return f"http://{parsed.hostname}:{parsed.port}"


def public_host(host, proxy=None, *, transport=None):
    if not proxy:
        return require_public_dns(host)
    proxy = local_browser_proxy(proxy)
    try:
        addresses = []
        with httpx.Client(
            proxy=proxy if transport is None else None,
            transport=transport,
            timeout=6,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            for kind in ("A", "AAAA"):
                with client.stream(
                    "GET",
                    "https://dns.google/resolve",
                    params={"name": host, "type": kind, "edns_client_subnet": "0.0.0.0/0"},
                    headers={"Accept-Encoding": "identity"},
                ) as response:
                    response.raise_for_status()
                    if response.headers.get("content-encoding", "identity") != "identity":
                        raise ValueError()
                    raw = bytearray()
                    for part in response.iter_bytes():
                        if len(raw) + len(part) > 64000:
                            raise ValueError()
                        raw.extend(part)
                result = json.loads(raw)
                if result.get("Status") != 0:
                    raise ValueError()
                addresses.extend(
                    row["data"] for row in result.get("Answer", []) if row.get("type") in {1, 28}
                )
        if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError, httpx.HTTPError):
        raise DomainError("BROWSER_PUBLIC_DNS_REQUIRED", 409) from None
