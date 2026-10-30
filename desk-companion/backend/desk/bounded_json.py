"""Bounded provider responses and pre-dispatch authorization fencing."""

import json
import time
from contextvars import ContextVar
from .store import DomainError

TEXT_RESPONSE_BYTES = 128 * 1024
TEXT_RESPONSE_DEADLINE = 30.0
TEXT_NETWORK_TIMEOUT = 5.0

# Per-call/thread/task scope, never a model argument or persistent authority.
_DISPATCH_CHECKPOINT = ContextVar("desk_text_dispatch_checkpoint", default=None)


class TextDispatchRefused(DomainError):
    """Known local denial before transport; distinct from an uncertain sent call."""


def _request_checkpoint(_request):
    checkpoint = _DISPATCH_CHECKPOINT.get()
    if checkpoint is not None:
        checkpoint(_request)


def bounded_json_post(client, endpoint, *, headers, json_body, clock=None):
    """Bound raw response storage and check elapsed time between network chunks.

    Phase inactivity timeout is enforced by HTTPX. This is not an OS-level
    hard deadline: header parsing/blocked system calls cannot be interrupted here.
    Never buffer/decompress an arbitrary provider body before checking its size.
    """
    clock = clock or time.monotonic
    deadline = clock() + TEXT_RESPONSE_DEADLINE
    with client.stream(
        "POST", endpoint, headers={**headers, "Accept-Encoding": "identity"}, json=json_body
    ) as response:
        response.raise_for_status()
        if response.headers.get("content-encoding", "identity").lower() != "identity":
            raise ValueError("Compressed provider response is not admitted")
        length = response.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > TEXT_RESPONSE_BYTES):
            raise ValueError("Provider response exceeds limit")
        body = bytearray()
        if clock() > deadline:
            raise ValueError("Provider response deadline exceeded")
        # No chunk_size: accumulating a large fixed chunk would hide tiny trickle
        # reads from the deadline check. Each raw transport chunk is checked.
        # MockTransport may supply a deliberately preloaded Response(json=...).
        # Production network responses remain unconsumed here; apply the same
        # byte/deadline checks to both paths without rereading a consumed stream.
        chunks = [response.content] if response.is_stream_consumed else response.iter_raw()
        for chunk in chunks:
            if clock() > deadline or len(body) + len(chunk) > TEXT_RESPONSE_BYTES:
                raise ValueError("Provider response exceeds budget")
            body.extend(chunk)
        if clock() > deadline:
            raise ValueError("Provider response deadline exceeded")
    try:
        value = json.loads(bytes(body))
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 64:
                raise ValueError("Provider JSON structure exceeds parser limits")
            if isinstance(item, dict):
                pending.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
        return value
    except RecursionError:
        raise ValueError("Provider JSON structure exceeds parser limits") from None
