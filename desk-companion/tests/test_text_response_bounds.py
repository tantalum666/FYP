"""Synthetic HTTP streams; no real provider calls or model-quality claims."""

import json

import httpx
import pytest

from desk.text_ai import bounded_json_post, TEXT_RESPONSE_BYTES, TEXT_NETWORK_TIMEOUT
from desk.text_ai import TextConfig, TextAssistant, FollowUpAdvice
from desk.runtime import Runtime
from desk.store import Store, DomainError


class Chunks(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
        self.reads = 0

    def __iter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    def close(self):
        self.closed = True


def client(stream, headers=None, status=200, seen=None):
    def transport(request):
        if seen is not None:
            seen.append(request)
        return httpx.Response(status, headers=headers, stream=stream)

    return httpx.Client(transport=httpx.MockTransport(transport), timeout=TEXT_NETWORK_TIMEOUT)


def test_streamed_json_and_identity_header():
    stream = Chunks([b'{"ok":', b"true}"])
    seen = []
    with client(stream, seen=seen) as c:
        assert bounded_json_post(c, "https://example.invalid", headers={}, json_body={}) == {
            "ok": True
        }
    assert stream.closed
    assert seen[0].headers["accept-encoding"] == "identity"
    assert seen[0].extensions["timeout"]["read"] == TEXT_NETWORK_TIMEOUT


@pytest.mark.parametrize(
    "headers",
    [
        {"content-length": str(TEXT_RESPONSE_BYTES + 1)},
        {"content-length": "-1"},
        {"content-encoding": "gzip"},
    ],
)
def test_rejects_declared_oversize_compression_and_invalid_length(headers):
    stream = Chunks([b"not read"])
    with client(stream, headers=headers) as c, pytest.raises(ValueError):
        bounded_json_post(c, "https://example.invalid", headers={}, json_body={})
    assert stream.closed and stream.reads == 0


def test_unknown_length_stream_stops_before_unbounded_body():
    stream = Chunks([b"x" * 8192] * 1000)
    with client(stream) as c, pytest.raises(ValueError):
        bounded_json_post(c, "https://example.invalid", headers={}, json_body={})
    assert stream.closed and stream.reads == 17


def test_trickle_deadline_checked_each_raw_chunk_without_fixed_chunk_buffer():
    stream = Chunks([b" "] * 1000)
    clock = [0.0]

    def tick():
        clock[0] += 1.0
        return clock[0]

    with client(stream) as c, pytest.raises(ValueError, match="budget"):
        bounded_json_post(c, "https://example.invalid", headers={}, json_body={}, clock=tick)
    assert stream.closed and stream.reads < 32


def test_time_after_headers_and_malformed_json_are_rejected():
    stream = Chunks([b"{}"])
    times = iter([0.0, 31.0])
    with client(stream) as c, pytest.raises(ValueError, match="deadline"):
        bounded_json_post(
            c, "https://example.invalid", headers={}, json_body={}, clock=lambda: next(times)
        )
    assert stream.reads == 0 and stream.closed
    stream = Chunks([b"not-json"])
    with client(stream) as c, pytest.raises(ValueError):
        bounded_json_post(c, "https://example.invalid", headers={}, json_body={})


@pytest.mark.parametrize("provider", ["gemini", "qwen"])
def test_existing_provider_protocol_uses_bounded_stream_and_retains_usage(tmp_path, provider):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    answer = json.dumps({"en": "Saved fact", "zh": "已存事实"})
    body = (
        {"choices": [{"message": {"content": answer}}], "usage": {"tokens": 4}}
        if provider == "qwen"
        else {
            "candidates": [{"content": {"parts": [{"text": answer}]}}],
            "usageMetadata": {"tokens": 4},
        }
    )
    stream = Chunks([json.dumps(body).encode()])
    cfg = TextConfig(
        provider=provider,
        model="fixture-model",
        api_key="fixture",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        if provider == "qwen"
        else "",
    )
    service = TextAssistant(
        runtime,
        config=cfg,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
    )
    assert service.generate("System", {}, FollowUpAdvice, "fixture").en == "Saved fact"
    with runtime.store.connection() as conn:
        assert json.loads(conn.execute("SELECT usage FROM text_ai_usage").fetchone()[0]) == {
            "tokens": 4
        }
    assert stream.closed


def test_oversized_provider_response_records_one_failed_attempt_without_retry(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    calls = []

    def transport(request):
        calls.append(request)
        return httpx.Response(200, stream=Chunks([b"x" * 8192] * 100))

    service = TextAssistant(
        runtime,
        config=TextConfig(provider="gemini", model="fixture", api_key="fixture"),
        transport=httpx.MockTransport(transport),
    )
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        service.generate("System", {}, FollowUpAdvice, "fixture")
    assert len(calls) == 1
    with runtime.store.connection() as conn:
        assert conn.execute("SELECT count(*) FROM text_ai_usage").fetchone()[0] == 1


def test_preloaded_mock_transport_retains_protocol_test_compatibility():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    ) as c:
        assert bounded_json_post(c, "https://example.invalid", headers={}, json_body={}) == {
            "ok": True
        }


def test_deeply_nested_bounded_json_is_normalized():
    stream = Chunks([b"[" * 20000 + b"0" + b"]" * 20000])
    with client(stream) as c, pytest.raises(ValueError, match="structure"):
        bounded_json_post(c, "https://example.invalid", headers={}, json_body={})
    assert stream.closed


def test_malformed_provider_parts_return_safe_unavailable(tmp_path):
    runtime = Runtime(Store(tmp_path, password="fixture-only"))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"candidates": [{"content": {"parts": [1]}}]})
    )
    service = TextAssistant(
        runtime,
        config=TextConfig(provider="gemini", model="fixture", api_key="fixture"),
        transport=transport,
    )
    with pytest.raises(DomainError, match="TEXT_AI_UNAVAILABLE"):
        service.generate("System", {}, FollowUpAdvice, "fixture")
