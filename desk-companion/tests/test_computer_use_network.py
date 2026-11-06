"""Explicit browser proxy and bounded public-DNS checks; no external network."""

import httpx
import pytest

from desk.computer_use_network import local_browser_proxy, public_host
from desk.store import DomainError


@pytest.mark.parametrize(
    "value",
    [
        "http://other.example:7897",
        "http://name:secret@127.0.0.1:7897",
        "socks5://127.0.0.1:7897",
        "http://127.0.0.1:7897/path",
        "http://127.0.0.1:7897?x=1",
    ],
)
def test_only_explicit_local_browser_proxy_is_accepted(value):
    with pytest.raises(ValueError):
        local_browser_proxy(value)


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.1.2.3", "169.254.169.254", "198.18.0.4", "::1"]
)
def test_proxy_dns_never_promotes_private_or_fake_ips_to_public(address):
    def response(request):
        assert request.url.host == "dns.google"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"Status": 0, "Answer": [{"type": 1, "data": address}]})

    with pytest.raises(DomainError, match="BROWSER_PUBLIC_DNS_REQUIRED"):
        public_host(
            "public.example", "http://127.0.0.1:7897", transport=httpx.MockTransport(response)
        )


def test_public_proxy_dns_checks_both_address_families():
    seen = []

    def response(request):
        seen.append(request.url.params["type"])
        return httpx.Response(200, json={"Status": 0, "Answer": [{"type": 1, "data": "8.8.8.8"}]})

    public_host("public.example", "http://127.0.0.1:7897", transport=httpx.MockTransport(response))
    assert seen == ["A", "AAAA"]
