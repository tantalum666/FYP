"""Session cookie flags. Secure follows the public HTTPS origin behind a local proxy."""

import os


def cookie_secure(request) -> bool:
    if request.url.scheme == "https":
        return True
    # Caddy terminates TLS and forwards HTTP. The app would otherwise store a
    # non-Secure cookie on an HTTPS site. Local http without this variable stays usable.
    return os.environ.get("DESK_PUBLIC_ORIGIN", "").startswith("https://")
