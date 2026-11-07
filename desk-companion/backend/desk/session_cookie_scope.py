"""Isolate loopback app cookies by the requested port.

Browsers share cookies across ports. A Mac preview and a forwarded Pi can have
independent owner stores on 127.0.0.1; neither may replace the other's session.
Internal handlers keep their existing cookie contract and authority checks.
"""

from http.cookies import CookieError, SimpleCookie
from urllib.parse import urlsplit

NAMES = {"desk_companion_session", "desk_companion_device"}


def loopback_suffix(headers):
    host = next((value.decode("latin1") for key, value in headers if key.lower() == b"host"), "")
    try:
        address = urlsplit("//" + host)
        if address.hostname in {"localhost", "127.0.0.1", "::1"} and address.port:
            return "_p" + str(address.port)
    except ValueError:
        pass
    return ""


class LoopbackCookieScope:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        suffix = loopback_suffix(scope.get("headers", []))
        if not suffix:
            return await self.app(scope, receive, send)
        parsed = SimpleCookie()
        try:
            for key, value in scope.get("headers", []):
                if key.lower() == b"cookie":
                    parsed.load(value.decode("latin1"))
        except CookieError:
            parsed = SimpleCookie()
        # An unscoped legacy cookie may belong to a different backend. The
        # existing trusted-local bootstrap handles the one-time reconnection.
        for name in NAMES:
            parsed.pop(name, None)
            if name + suffix in parsed:
                parsed[name] = parsed[name + suffix].value
        headers = [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"cookie"]
        if parsed:
            headers.append(
                (b"cookie", "; ".join(m.OutputString() for m in parsed.values()).encode("latin1"))
            )
        scope = {**scope, "headers": headers}

        async def scoped_send(message):
            if message["type"] == "http.response.start":
                response_headers = []
                for key, value in message.get("headers", []):
                    if key.lower() == b"set-cookie":
                        text = value.decode("latin1")
                        name, separator, rest = text.partition("=")
                        if name in NAMES and separator:
                            value = (name + suffix + "=" + rest).encode("latin1")
                    response_headers.append((key, value))
                message = {**message, "headers": response_headers}
            await send(message)

        await self.app(scope, receive, scoped_send)
