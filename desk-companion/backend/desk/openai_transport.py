"""Explicit OpenAI-only loopback transport; never inherit a general proxy."""

import re

OPENAI_API = "https://api.openai.com/v1"
SESSION_ID = re.compile(r"sess_[a-zA-Z0-9_-]{1,120}")


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


def numeric_usage(value):
    if not isinstance(value, dict):
        return None
    result = {
        key: value[key]
        for key in ("input_tokens", "output_tokens", "total_tokens")
        if type(value.get(key)) is int and value[key] >= 0
    }
    for parent, child in (
        ("input_tokens_details", "cached_tokens"),
        ("output_tokens_details", "reasoning_tokens"),
    ):
        details = value.get(parent)
        count = details.get(child) if isinstance(details, dict) else None
        if type(count) is int and count >= 0:
            result[parent] = {child: count}
    return result or None
