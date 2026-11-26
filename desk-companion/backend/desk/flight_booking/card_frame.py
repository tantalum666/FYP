"""A loopback-only static origin for the test card SDK, separate from the owner's desk."""

from pathlib import Path

from fastapi.responses import FileResponse, Response

HOST = "nuitee-card.localhost"
FRAME = "nuitee-sandbox-card.html"
SCRIPT = "nuitee-sandbox-card.js"
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def frame_origin(request):
    host = request.url.hostname
    if host not in LOOPBACK | {HOST} or request.url.scheme not in {"http", "https"}:
        return None
    port = f":{request.url.port}" if request.url.port else ""
    return f"{request.url.scheme}://{HOST}{port}"


def static_response(request, dist: Path, enabled):
    if request.url.hostname != HOST:
        return None
    name = request.url.path.lstrip("/")
    if not enabled or request.method not in {"GET", "HEAD"} or name not in {FRAME, SCRIPT}:
        return Response(status_code=404)
    try:
        from ipaddress import ip_address

        if not ip_address(request.client.host).is_loopback:
            return Response(status_code=403)
    except (ValueError, AttributeError):
        return Response(status_code=403)
    target = dist / name
    if not target.is_file():
        return Response(status_code=404)
    port = f":{request.url.port}" if request.url.port else ""
    parents = " ".join(
        f"{request.url.scheme}://{h}{port}" for h in ("127.0.0.1", "localhost", "[::1]")
    )
    return FileResponse(
        target,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; script-src 'self' https://js.stripe.com; "
                "frame-src https://js.stripe.com https://hooks.stripe.com https://*.stripe.network; "
                "connect-src https://api.stripe.com https://*.stripe.com https://*.stripe.network; "
                "img-src https://*.stripe.com data:; style-src 'unsafe-inline'; "
                f"base-uri 'none'; form-action 'none'; frame-ancestors {parents} capacitor://localhost"
            ),
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        },
    )
