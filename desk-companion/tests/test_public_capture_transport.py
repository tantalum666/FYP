"""Byte-preserving offline sockets; no live DNS/TLS/public request."""

import http.client
import socket
import threading
import time
import pytest
from desk.connectors import mcp_transport, public_https
from desk.connectors import public_capture_transport as transport
from desk.connectors.public_capture_transport import PublicCaptureClient, is_public_unicast
from desk.connectors.schema import ConnectorError
from desk.store import DomainError

URL = "https://example.com/page"


class ByteSocket:
    def __init__(self, payload, *, stride=None, tick=None):
        self.payload, self.stride, self.tick = payload, stride, tick
        self.sent, self.timeouts, self.closed = [], [], False

    def recv_into(self, buffer):
        if self.tick:
            self.tick()
        size = min(len(buffer), len(self.payload), self.stride or len(buffer))
        buffer[:size], self.payload = self.payload[:size], self.payload[size:]
        return size

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, value):
        self.timeouts.append(value)

    def close(self):
        self.closed = True


def client_for(sock):
    class Connection(http.client.HTTPConnection):
        def connect(self):
            self.sock = sock

    class Client(PublicCaptureClient):
        def _connection(self, host, deadline, checkpoint):
            checkpoint()
            return Connection(host)

    return Client()


def payload(body=b"hello", *, status=b"200 OK", headers=None):
    if headers is None:
        headers = [
            b"Content-Type: text/plain; charset=utf-8",
            b"Content-Length: " + str(len(body)).encode(),
        ]
    return b"HTTP/1.1 " + status + b"\r\n" + b"\r\n".join(headers) + b"\r\n\r\n" + body


def failure(raw, code, *, stride=None):
    sock = ByteSocket(raw, stride=stride)
    with pytest.raises(DomainError) as error:
        client_for(sock).fetch(URL)
    assert error.value.code == code
    assert sock.closed
    assert b"".join(sock.sent).count(b"GET ") == 1


def test_exact_get_fixed_headers_complete_bytes_local_cleanup(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://secret.invalid")
    sock = ByteSocket(
        payload(
            headers=[b"Content-Length: 5", b"Content-Type: text/markdown", b"Set-Cookie: secret=x"]
        )
    )
    marks = []
    response = client_for(sock).fetch(URL, on_dispatch=lambda: marks.append(len(sock.sent)))
    assert response.raw == b"hello" and response.mime_type == "text/markdown"
    assert b"".join(sock.sent) == (
        b"GET /page HTTP/1.1\r\nHost: example.com\r\n"
        b"Accept: text/plain, text/markdown, text/html\r\nAccept-Encoding: identity\r\n"
        b"User-Agent: DeskCompanion-PublicCapture/1\r\nConnection: close\r\n\r\n"
    )
    assert marks == [0] and sock.closed
    assert all(0 < timeout <= 3 for timeout in sock.timeouts)
    assert not hasattr(response, "headers")


@pytest.mark.parametrize(
    "status,code",
    [
        (b"100 Continue", "CAPTURE_INTERIM_DENIED"),
        (b"101 Switching Protocols", "CAPTURE_INTERIM_DENIED"),
        (b"103 Early Hints", "CAPTURE_INTERIM_DENIED"),
        (b"302 Found", "CAPTURE_REDIRECT_DENIED"),
        (b"401 Unauthorized", "CAPTURE_AUTH_REQUIRED"),
        (b"403 Forbidden", "CAPTURE_AUTH_REQUIRED"),
        (b"429 Slow Down", "CAPTURE_HTTP_ERROR"),
        (b"204 No Content", "CAPTURE_HTTP_ERROR"),
    ],
)
def test_status_never_redirects_retries_authenticates_or_cancels(status, code):
    failure(payload(status=status) + payload(), code)


@pytest.mark.parametrize(
    "extra,code",
    [
        ([b"content-length: 5"], "CAPTURE_FRAMING_INVALID"),
        ([b"Transfer-Encoding: identity"], "CAPTURE_FRAMING_INVALID"),
        ([b"Transfer-Encoding: chunked"], "CAPTURE_FRAMING_INVALID"),
        ([b"Upgrade: h2c"], "CAPTURE_FRAMING_INVALID"),
        ([b"content-type: text/plain"], "CAPTURE_FRAMING_INVALID"),
        ([b"Content-Encoding: identity", b"Content-Encoding: identity"], "CAPTURE_FRAMING_INVALID"),
        ([b"Content-Encoding: gzip"], "CAPTURE_ENCODING_DENIED"),
        ([b" continuation"], "CAPTURE_FRAMING_INVALID"),
        ([b"\tcontinuation"], "CAPTURE_FRAMING_INVALID"),
        ([b"Content-Length : 5"], "CAPTURE_FRAMING_INVALID"),
        ([b"Broken"], "CAPTURE_FRAMING_INVALID"),
        ([b"X: bad\x00value"], "CAPTURE_FRAMING_INVALID"),
    ],
)
def test_strict_raw_headers(extra, code):
    failure(payload(headers=[b"Content-Length: 5", b"Content-Type: text/plain"] + extra), code)


@pytest.mark.parametrize("length", [b"5, 5", b"+5", b"05", b"0", b"131073", b"-5"])
def test_noncanonical_length_denied(length):
    failure(
        payload(headers=[b"Content-Length: " + length, b"Content-Type: text/plain"]),
        "CAPTURE_RESPONSE_LIMIT",
    )


@pytest.mark.parametrize(
    "mime", [b"application/json", b"application/xml", b"text/plain; charset=iso-8859-1"]
)
def test_unsupported_mime(mime):
    failure(
        payload(headers=[b"Content-Length: 5", b"Content-Type: " + mime]),
        "CAPTURE_CONTENT_TYPE_DENIED",
    )


@pytest.mark.parametrize("headers", [[b"Content-Type: text/plain"], [b"Content-Length: 5"]])
def test_missing_required_header(headers):
    failure(payload(headers=headers), "CAPTURE_FRAMING_INVALID")


@pytest.mark.parametrize(
    "raw",
    [
        payload().replace(b"\r\n", b"\n"),
        payload().replace(b"200 OK\r\n", b"200 OK\n"),
        payload().replace(b"Content-Length: 5\r\n", b"Content-Length: 5\n"),
        payload().replace(b"HTTP/1.1", b"HTTP/2.0"),
        payload().replace(b"HTTP/1.1 200", b"HTTP/1.1  200"),
    ],
)
def test_noncanonical_status_or_non_crlf_rejected(raw):
    failure(raw, "CAPTURE_FRAMING_INVALID")


def test_truncated_body_never_partial_success():
    failure(payload()[:-1], "CAPTURE_BODY_INCOMPLETE")


def test_exact_body_limit():
    body = b"x" * 131072
    sock = ByteSocket(payload(body), stride=4096)
    assert client_for(sock).fetch(URL).raw == body and sock.closed
    failure(payload(body + b"x"), "CAPTURE_RESPONSE_LIMIT")


def test_conservative_header_read_ahead_guard_not_relaxed():
    raw = payload(
        b"x" * 8000,
        headers=[b"Content-Type: text/plain", b"Content-Length: 8000", b"X-Pad: " + b"x" * 15500],
    )
    assert len(raw.split(b"\r\n\r\n")[0]) + 4 < 16384
    failure(raw, "CAPTURE_HEADERS_LIMIT", stride=3000)
    sock = ByteSocket(
        payload(
            headers=[b"Content-Type: text/plain", b"Content-Length: 5", b"X-Pad: " + b"x" * 14000]
        )
    )
    assert client_for(sock).fetch(URL).raw == b"hello"


def test_header_limit_single_byte_reads():
    sock = ByteSocket(payload(headers=[b"X-Pad: " + b"x" * 16384]), stride=1)
    with pytest.raises(DomainError) as error:
        client_for(sock).fetch(URL)
    assert error.value.code == "CAPTURE_HEADERS_LIMIT" and sock.closed


@pytest.mark.parametrize(
    "address",
    [
        "224.0.0.1",
        "ff02::1",
        "ff0e::1",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "::",
        "10.0.0.1",
        "169.254.169.254",
        "198.18.0.144",
        "240.0.0.1",
        "::ffff:127.0.0.1",
        "fe80::1",
        "2606:4700:4700::1111%eth0",
        "invalid",
    ],
)
def test_nonpublic_unicast_denied(address):
    assert not is_public_unicast(address)


@pytest.mark.parametrize(
    "address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111", "::ffff:93.184.216.34"]
)
def test_public_unicast(address):
    assert is_public_unicast(address)


def dns_answers(monkeypatch, addresses):
    calls = []

    def resolve(*args, **kwargs):
        calls.append((args, kwargs))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    return calls


def test_multicast_capture_denied_mcp_historical_semantics_preserved(monkeypatch):
    calls = dns_answers(monkeypatch, ["224.0.0.1"])
    assert mcp_transport.public_addresses("example.com") == ["224.0.0.1"]
    with pytest.raises(DomainError) as error:
        PublicCaptureClient().fetch(URL)
    assert error.value.code == "CAPTURE_PUBLIC_DNS_REQUIRED" and len(calls) == 2


@pytest.mark.parametrize(
    "addresses",
    [["93.184.216.34", "224.0.0.1"], ["1.1.1.1", "127.0.0.1"], ["ff02::1"], ["::ffff:127.0.0.1"]],
)
def test_entire_dns_answer_denied(monkeypatch, addresses):
    calls = dns_answers(monkeypatch, addresses)
    monkeypatch.setattr(socket, "socket", lambda *_: pytest.fail("must not create socket"))
    with pytest.raises(DomainError) as error:
        PublicCaptureClient().fetch(URL)
    assert error.value.code == "CAPTURE_PUBLIC_DNS_REQUIRED" and len(calls) == 1


def test_shared_resolver_slot_error_mapping():
    assert mcp_transport._DNS_SLOT is public_https._DNS_SLOT
    assert public_https._DNS_SLOT.acquire(blocking=False)
    try:
        with pytest.raises(DomainError) as capture:
            PublicCaptureClient().fetch(URL)
        with pytest.raises(ConnectorError) as mcp:
            mcp_transport.public_addresses("example.com")
        assert capture.value.code == "CAPTURE_RESOLVER_BUSY" and capture.value.status == 503
        assert mcp.value.code == "CONNECTOR_RESOLVER_BUSY" and mcp.value.status == 503
    finally:
        public_https._DNS_SLOT.release()


def test_blocked_resolver_never_connects_late(monkeypatch):
    release, finished = threading.Event(), threading.Event()

    def resolve(*_, **__):
        release.wait(2)
        finished.set()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(socket, "socket", lambda *_: pytest.fail("late socket"))
    try:
        with pytest.raises(DomainError) as error:
            PublicCaptureClient().fetch(URL, deadline=time.monotonic() + 0.03)
        assert error.value.code == "CAPTURE_DEADLINE"
        with pytest.raises(ConnectorError) as error:
            mcp_transport.public_addresses("other.example")
        assert error.value.code == "CONNECTOR_RESOLVER_BUSY"
    finally:
        release.set()
        assert finished.wait(1)
        for _ in range(100):
            if public_https._DNS_SLOT.acquire(blocking=False):
                public_https._DNS_SLOT.release()
                break
            time.sleep(0.001)


def test_single_resolver_pinned_socket_original_tls_host(monkeypatch):
    calls = dns_answers(monkeypatch, ["93.184.216.34", "1.1.1.1"])
    events, sock = [], ByteSocket(payload())
    sock.connect = lambda address: events.append(("connect", address))

    class Context:
        check_hostname, verify_mode, post_handshake_auth = True, 2, False

        def set_alpn_protocols(self, _):
            pass

        def wrap_socket(self, raw, server_hostname):
            events.append(("tls", server_hostname))
            return raw

    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *args: events.append(("socket", args)) or sock)
    assert PublicCaptureClient().fetch(URL).raw == b"hello"
    assert len(calls) == 1 and sock.closed
    assert events == [
        ("socket", (socket.AF_INET, socket.SOCK_STREAM)),
        ("connect", ("1.1.1.1", 443)),
        ("tls", "example.com"),
    ]


@pytest.mark.parametrize("phase", ["headers", "body"])
def test_slow_drip_total_deadline(monkeypatch, phase):
    now = [100.0]
    monkeypatch.setattr(transport.time, "monotonic", lambda: now[0])
    sock = ByteSocket(
        payload(b"x" * 1000), stride=1, tick=lambda: now.__setitem__(0, now[0] + 0.01)
    )
    with pytest.raises(DomainError) as error:
        client_for(sock).fetch(URL, deadline=100.05 if phase == "headers" else 101.1)
    assert error.value.code == "CAPTURE_DEADLINE" and sock.closed
    assert len(sock.sent) == 1


def test_cancel_before_after_dispatch_no_cleanup_request():
    for after_send in (False, True):
        sock, armed = ByteSocket(payload(), stride=1), [False]

        def check():
            if armed[0] and (not after_send or sock.sent):
                raise DomainError("CAPTURE_CANCELLED", 409)

        with pytest.raises(DomainError) as error:
            client_for(sock).fetch(URL, check, on_dispatch=lambda: armed.__setitem__(0, True))
        assert error.value.code == "CAPTURE_CANCELLED" and sock.closed
        assert len(sock.sent) == (1 if after_send else 0)


def test_invalid_url_expired_deadline_zero_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: pytest.fail("DNS"))
    with pytest.raises(DomainError):
        PublicCaptureClient().fetch("http://example.com/page")
    with pytest.raises(DomainError) as error:
        PublicCaptureClient().fetch(URL, deadline=time.monotonic() - 1)
    assert error.value.code == "CAPTURE_DEADLINE"


@pytest.mark.parametrize("phase", ["connect", "tls"])
def test_connect_or_tls_failure_closes_raw_socket_no_alternate(monkeypatch, phase):
    calls = dns_answers(monkeypatch, ["1.1.1.1", "93.184.216.34"])
    sock, events = ByteSocket(payload()), []

    def connect(address):
        events.append(("connect", address))
        if phase == "connect":
            raise OSError("fixture refused")

    sock.connect = connect

    class Context:
        check_hostname, verify_mode, post_handshake_auth = True, 2, False

        def set_alpn_protocols(self, _):
            pass

        def wrap_socket(self, raw, server_hostname):
            events.append(("tls", server_hostname))
            raise public_https.ssl.SSLCertVerificationError("fixture certificate rejection")

    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *_: sock)
    with pytest.raises(DomainError) as error:
        PublicCaptureClient().fetch(URL)
    assert error.value.code == "CAPTURE_TRANSPORT_FAILED"
    assert len(calls) == 1 and sock.closed and not sock.sent
    assert [e for e in events if e[0] == "connect"] == [("connect", ("1.1.1.1", 443))]


def test_cancellation_after_tcp_prevents_tls_and_dispatch(monkeypatch):
    dns_answers(monkeypatch, ["1.1.1.1"])
    sock, connected = ByteSocket(payload()), [False]
    sock.connect = lambda _: connected.__setitem__(0, True)

    class Context:
        check_hostname, verify_mode, post_handshake_auth = True, 2, False

        def set_alpn_protocols(self, _):
            pass

        def wrap_socket(self, *_, **__):
            pytest.fail("TLS after cancellation")

    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *_: sock)

    def check():
        if connected[0]:
            raise DomainError("CAPTURE_CANCELLED", 409)

    with pytest.raises(DomainError) as error:
        PublicCaptureClient().fetch(URL, check)
    assert error.value.code == "CAPTURE_CANCELLED" and sock.closed and not sock.sent


def test_cancellation_during_body_fences_success():
    sock = ByteSocket(payload(b"x" * 1000), stride=1)

    def check():
        if len(sock.payload) < 500:
            raise DomainError("CAPTURE_CANCELLED", 409)

    with pytest.raises(DomainError) as error:
        client_for(sock).fetch(URL, check)
    assert error.value.code == "CAPTURE_CANCELLED" and sock.closed and len(sock.sent) == 1


def test_socket_timeout_during_headers_and_body_is_safe_failure():
    for phase in ("headers", "body"):
        sock = ByteSocket(payload(b"x" * 1000), stride=1)

        def tick():
            if phase == "headers" or len(sock.payload) < 500:
                raise TimeoutError("fixture timeout with private text")

        sock.tick = tick
        with pytest.raises(DomainError) as error:
            client_for(sock).fetch(URL)
        assert error.value.code == "CAPTURE_TRANSPORT_FAILED" and sock.closed
        assert "private" not in str(error.value)
