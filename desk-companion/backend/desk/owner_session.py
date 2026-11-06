"""Passwordless opening of the owner's directly connected local workspace."""

from urllib.parse import urlsplit


def local_owner_available(request, *, public_origin="", enabled=True):
    if not enabled or public_origin or request.client is None:
        return False
    if request.client.host not in {"127.0.0.1", "::1"}:
        return False
    if request.url.hostname not in {"localhost", "127.0.0.1"}:
        return False
    if any(name in request.headers for name in ("forwarded", "x-forwarded-for", "x-forwarded-host")):
        return False
    origin = request.headers.get("origin")
    if origin:
        parts = urlsplit(origin)
        if parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1"}:
            return False
    return True
