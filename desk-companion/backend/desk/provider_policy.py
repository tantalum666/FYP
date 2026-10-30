"""Exact, fail-closed destinations for credential-bearing model connections.

This validates configuration, not account access or a model's regional availability.
Endpoints never come from model tool arguments. New providers require their own
reviewed policy; a plausible HTTPS/WSS URL is not sufficient authorization.
"""

import re
from urllib.parse import urlsplit

import websockets


GEMINI_TEXT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_VOICE_ENDPOINT = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
QWEN_TEXT_PATH = "/compatible-mode/v1/chat/completions"
QWEN_VOICE_PATH = "/api-ws/v1/realtime"
QWEN_SHARED_HOSTS = {
    "dashscope.aliyuncs.com",
    "dashscope-intl.aliyuncs.com",
    "dashscope-us.aliyuncs.com",
}
QWEN_TEXT_REGIONS = {
    "cn-beijing",
    "ap-southeast-1",
    "ap-northeast-1",
    "eu-central-1",
    "us-east-1",
    "cn-hongkong",
}
QWEN_VOICE_REGIONS = {"cn-beijing", "ap-southeast-1"}


def valid_model(model, *, gemini_voice=False):
    if not isinstance(model, str):
        return False
    if gemini_voice:
        model = model.removeprefix("models/")
    return bool(re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model))


def valid_api_key(key):
    # Do not normalize secrets or let control characters reach an HTTP header.
    return bool(
        isinstance(key, str)
        and key
        and key == key.strip()
        and all(32 <= ord(char) < 127 for char in key)
    )


def _qwen_host(host, kind):
    shared = (
        QWEN_SHARED_HOSTS if kind == "text" else QWEN_SHARED_HOSTS - {"dashscope-us.aliyuncs.com"}
    )
    if host in shared:
        return True
    labels = host.split(".")
    regions = QWEN_TEXT_REGIONS if kind == "text" else QWEN_VOICE_REGIONS
    return bool(
        len(labels) == 5
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", labels[0])
        and labels[1] in regions
        and labels[2:] == ["maas", "aliyuncs", "com"]
    )


def valid_provider_endpoint(provider, endpoint, *, kind):
    if kind not in {"text", "voice"} or not isinstance(endpoint, str):
        return False
    if provider == "gemini" and endpoint == "":
        return True  # The caller substitutes the pinned default for this channel.
    if (
        not endpoint
        or not endpoint.isascii()
        or any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 or char in "\\?#"
            for char in endpoint
        )
    ):
        return False
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname
        # Exact authority disallows userinfo, ports (including empty/invalid),
        # encoded hosts, trailing dots and IPv6 literals without parser ambiguity.
        if not host or parsed.netloc.lower() != host or parsed.port is not None:
            return False
    except (ValueError, TypeError):
        return False
    if parsed.scheme != ("https" if kind == "text" else "wss"):
        return False
    if provider == "gemini":
        expected = urlsplit(GEMINI_TEXT_ENDPOINT if kind == "text" else GEMINI_VOICE_ENDPOINT)
        return host == expected.hostname and parsed.path == expected.path
    if provider != ("qwen" if kind == "text" else "qwen_audio"):
        return False
    return _qwen_host(host, kind) and parsed.path == (
        QWEN_TEXT_PATH if kind == "text" else QWEN_VOICE_PATH
    )


class ProviderWebSocketConnect(websockets.connect):
    """Never forward provider authentication headers through an HTTP redirect."""

    def process_redirect(self, exc):
        return exc
