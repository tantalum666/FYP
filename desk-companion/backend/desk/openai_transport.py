"""Explicit OpenAI-only loopback transport; never inherit a general proxy."""

import re


def validate_openai_proxy(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not re.fullmatch(
        r"http://127\.0\.0\.1:([1-9][0-9]{0,4})", value
    ):
        raise ValueError("Use an explicit OpenAI loopback HTTP CONNECT listener")
    port = int(value.rsplit(":", 1)[1])
    if not 1024 <= port <= 65535:
        raise ValueError("Use an unprivileged loopback port")
    return value


def model_proxy(config, transport=None):
    """Injected test transports remain offline even when the operator has a proxy."""
    if config.provider not in {"openai", "openai_realtime", "openai_live"}:
        return None
    proxy = validate_openai_proxy(getattr(config, "proxy_url", ""))
    return proxy if transport is None else None
