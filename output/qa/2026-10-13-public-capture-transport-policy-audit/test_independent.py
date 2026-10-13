"""Independent byte-socket audit. No external network or real user data."""

import http.client
import socket
import ssl
from types import SimpleNamespace
import pytest
from desk.connectors import public_capture_transport as transport
from desk.connectors import public_https, mcp_transport
from desk.public_capture_policy import extract_static_text, build_intent, CaptureIntent
from desk.store import DomainError
from desk.connectors.schema import ConnectorError


class BytesSocket:
    def __init__(self, data, stride=4096):
        self.data = data
        self.stride = stride
        self.sent = []
        self.closed = False
        self.timeouts = []

    def recv_into(self, target):
        n = min(len(target), self.stride, len(self.data))
        target[:n] = self.data[:n]
        self.data = self.data[n:]
        return n

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, t):
        self.timeouts.append(t)

    def close(self):
        self.closed = True


def frame(body=b"hello", headers=b"", status=b"200 OK"):
    return (
        b"HTTP/1.1 "
        + status
        + b"\r\nContent-Type: text/plain\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\n"
        + headers
        + b"\r\n"
        + body
    )


def client(sock):
    class Conn(http.client.HTTPConnection):
        def connect(self):
            self.sock = sock

    class Client(transport.PublicCaptureClient):
        def _connection(self, *a):
            return Conn("example.org")

    return Client()


@pytest.mark.parametrize("suffix", [b"EXTRA", frame(b"other"), b"\x00", b"\r\n"])
def test_content_length_frame_semantics_not_eof(suffix):
    sock = BytesSocket(frame() + suffix)
    result = client(sock).fetch("https://example.org/")
    assert result.raw == b"hello" and sock.closed and len(sock.sent) == 1


@pytest.mark.parametrize(
    "raw,code",
    [
        (frame()[:-1], "CAPTURE_BODY_INCOMPLETE"),
        (frame(status=b"199 Interim") + frame(), "CAPTURE_INTERIM_DENIED"),
        (frame(headers=b"Content-Length:\t5\r\n"), "CAPTURE_FRAMING_INVALID"),
        (frame(headers=b"Transfer-Encoding:\r\n"), "CAPTURE_FRAMING_INVALID"),
        (frame(headers=b"Content-Encoding: br\r\n"), "CAPTURE_ENCODING_DENIED"),
        (frame(headers=b"X-Test: x\rY: z\r\n"), "CAPTURE_FRAMING_INVALID"),
        (frame(headers=b"X-Test: x\x7f\r\n"), "CAPTURE_FRAMING_INVALID"),
        (frame(headers=b" Content-Type: text/html\r\n"), "CAPTURE_FRAMING_INVALID"),
        (
            frame().replace(b"Content-Length: 5", b"Content-Length: " + b"9" * 5000),
            "CAPTURE_RESPONSE_LIMIT",
        ),
    ],
)
def test_adversarial_raw_frames(raw, code):
    sock = BytesSocket(raw, 1)
    with pytest.raises(DomainError) as err:
        client(sock).fetch("https://example.org/")
    assert err.value.code == code and sock.closed and len(sock.sent) == 1


@pytest.mark.parametrize(
    "tail",
    [b'<p a="xxx', b"<!--noend", b'<p a="<no>', b"<!DOCTYPE html", b'<p a="' + b"x" * 120000],
)
def test_unfinished_lexical_tail_rejected_after_visible_prefix(tail):
    with pytest.raises(DomainError) as err:
        extract_static_text(b"<p>visible</p>" + tail, "text/html")
    assert err.value.code == "CAPTURE_HTML_MALFORMED"


@pytest.mark.parametrize(
    "html",
    [
        b"<p>not <b>approved</b>; only if verified</p>",
        b"<p>not approved; only if verified</p><span hidden>approved</span>",
        b"<p>not approved; only if verified</p><!--approved-->",
        b'<p>not approved; only if verified</p><template><a href="https://evil.invalid/">approved</a></template>',
    ],
)
def test_negations_survive_and_remote_instructions_are_data(html, monkeypatch):
    monkeypatch.setattr(socket, "socket", lambda *a: pytest.fail("socket"))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("DNS"))
    assert extract_static_text(html, "text/html").body == b"not approved; only if verified\n"


@pytest.mark.parametrize(
    "field,value",
    [
        ("capture_id", "b" * 32),
        ("url", "https://other.org/"),
        ("label", "other"),
        ("session_hash", "other"),
        ("privacy_revision", "other"),
    ],
)
def test_intent_digest_binds_each_identity(field, value):
    args = dict(
        capture_id="a" * 32,
        url="https://example.org/",
        label="label",
        session_hash="session",
        privacy_revision="privacy",
    )
    before = CaptureIntent(**build_intent(**args)).digest()
    args[field] = value
    assert CaptureIntent(**build_intent(**args)).digest() != before


@pytest.mark.parametrize("point", ["tcp", "tls", "send", "headers", "body"])
def test_cleanup_and_one_or_zero_get_on_cancel(point, monkeypatch):
    sock = BytesSocket(frame(b"x" * 5000), stride=1)
    events = []

    class Context:
        check_hostname = True
        verify_mode = ssl.CERT_REQUIRED
        post_handshake_auth = False

        def set_alpn_protocols(self, *a):
            pass

        def wrap_socket(self, raw, server_hostname):
            events.append("tls")
            return raw

    sock.connect = lambda address: events.append("tcp")
    oldsend = sock.sendall

    def send(data):
        oldsend(data)
        events.append("send")

    sock.sendall = send
    oldrecv = sock.recv_into

    def recv(buf):
        result = oldrecv(buf)
        if len(sock.data) < 5000:
            events.append("body")
        else:
            events.append("headers")
        return result

    sock.recv_into = recv
    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *a: sock)
    monkeypatch.setattr(transport, "public_addresses", lambda *a, **k: ["1.1.1.1"])

    def check():
        if point in events:
            raise DomainError("CANCELLED", 409)

    with pytest.raises(DomainError) as err:
        transport.PublicCaptureClient().fetch("https://example.org/", check)
    assert err.value.code == "CANCELLED" and sock.closed and len(sock.sent) <= 1


@pytest.mark.parametrize("fail_tls", [False, True])
def test_tcp_tls_remaining_timeout_and_failure_close(fail_tls, monkeypatch):
    now = [100.0]
    sock = BytesSocket(frame())
    events = []
    monkeypatch.setattr(transport.time, "monotonic", lambda: now[0])
    sock.connect = lambda address: now.__setitem__(0, 102.5)

    class Context:
        check_hostname = True
        verify_mode = ssl.CERT_REQUIRED
        post_handshake_auth = False

        def set_alpn_protocols(self, *a):
            pass

        def wrap_socket(self, raw, server_hostname):
            events.append(server_hostname)
            if fail_tls:
                raise ssl.SSLError("fixture")
            return raw

    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *a: sock)
    monkeypatch.setattr(transport, "public_addresses", lambda *a, **k: ["1.1.1.1"])
    if fail_tls:
        with pytest.raises(DomainError) as err:
            transport.PublicCaptureClient().fetch("https://example.org/", deadline=103)
        assert err.value.code == "CAPTURE_TRANSPORT_FAILED"
    else:
        assert (
            transport.PublicCaptureClient().fetch("https://example.org/", deadline=103).raw
            == b"hello"
        )
    assert sock.timeouts[:2] == [3, 0.5] and sock.closed and events == ["example.org"]
    assert len(sock.sent) == (0 if fail_tls else 1)


@pytest.mark.parametrize(
    "status,headers,body,code",
    [
        (b"302 Found", b"", b"{}", "CONNECTOR_REDIRECT_DENIED"),
        (b"401 Unauthorized", b"", b"{}", "CONNECTOR_AUTH_REQUIRED"),
        (b"200 OK", b"Content-Encoding: gzip\r\n", b"{}", "CONNECTOR_ENCODING_DENIED"),
        (b"200 OK", b"", b'{"jsonrpc":"2.0","id":"x","error":{}}', "CONNECTOR_RPC_ERROR"),
    ],
)
def test_mcp_taxonomy_with_extracted_reader(status, headers, body, code):
    raw = frame(body, headers, status).replace(b"text/plain", b"application/json")
    sock = BytesSocket(raw)

    class Conn(http.client.HTTPConnection):
        def connect(self):
            self.sock = sock

    class MCP(mcp_transport.McpHttpClient):
        def _connection(self):
            return Conn("example.org")

    c = MCP(SimpleNamespace(endpoint="https://example.org/mcp"))
    with pytest.raises(ConnectorError) as err:
        c._exchange({"jsonrpc": "2.0", "id": "x", "method": "fixture"}, lambda: None)
    assert err.value.code == code and sock.closed
    assert len(sock.sent) == 2 and sock.sent[0].startswith(b"POST /mcp ")


def test_mcp_still_accepts_interim_then_json():
    body = b'{"jsonrpc":"2.0","id":"x","result":{"ok":true}}'
    sock = BytesSocket(
        b"HTTP/1.1 100 Continue\r\n\r\n" + frame(body).replace(b"text/plain", b"application/json")
    )

    class Conn(http.client.HTTPConnection):
        def connect(self):
            self.sock = sock

    class MCP(mcp_transport.McpHttpClient):
        def _connection(self):
            return Conn("example.org")

    assert MCP(SimpleNamespace(endpoint="https://example.org/mcp"))._exchange(
        {"id": "x", "method": "fixture"}, lambda: None
    ) == {"ok": True}
    assert sock.closed


@pytest.mark.parametrize(
    "payload",
    [
        '<p a="' + "x" * 120000 + '">visible</p>',
        "<p>visible</p><!--" + "x" * 120000 + "-->",
    ],
)
def test_large_tokens_cancel_during_parse_feed(payload):
    calls = [0]
    validation = (len(payload) + 1023) // 1024

    def checkpoint():
        calls[0] += 1
        if calls[0] == validation + 5:
            raise DomainError("CANCELLED_DURING_PARSE", 409)

    with pytest.raises(DomainError) as err:
        extract_static_text(payload.encode(), "text/html", checkpoint)
    assert err.value.code == "CANCELLED_DURING_PARSE" and calls[0] == validation + 5


@pytest.mark.parametrize(
    "raw",
    [
        b"\xf0\x80\x80\xaf",
        b"\xed\xa0\x80",
        b"\xc0\x80",
        b"abc\xe2\x82",
    ],
)
def test_noncanonical_utf8_fails_before_partial_output(raw):
    with pytest.raises(DomainError) as err:
        extract_static_text(raw, "text/plain")
    assert err.value.code == "CAPTURE_UTF8_REQUIRED"


@pytest.mark.parametrize(
    "body,expected",
    [
        ("否" * 341 + "A", ("否" * 341 + "\nA\n").encode()),
        ("x\x85y\u2028z\u2029w\r\nv\ru", b"x\ny\nz\nw\nv\nu\n"),
    ],
)
def test_line_budget_exact_unicode_and_separators(body, expected):
    out = extract_static_text(body.encode(), "text/plain").body
    assert out == expected and all(len(line) <= 1024 for line in out.splitlines(keepends=True))


def test_send_timeout_tracks_remaining_total_budget_after_tls(monkeypatch):
    now = [100.0]
    sock = BytesSocket(frame())
    observed = []
    monkeypatch.setattr(transport.time, "monotonic", lambda: now[0])
    sock.connect = lambda address: None

    class Context:
        check_hostname = True
        verify_mode = ssl.CERT_REQUIRED
        post_handshake_auth = False

        def set_alpn_protocols(self, *a):
            pass

        def wrap_socket(self, raw, server_hostname):
            now[0] = 102.9
            return raw

    oldsend = sock.sendall

    def send(data):
        observed.append((sock.timeouts[-1], 103 - now[0]))
        oldsend(data)

    sock.sendall = send
    monkeypatch.setattr(public_https.ssl, "create_default_context", Context)
    monkeypatch.setattr(socket, "socket", lambda *a: sock)
    monkeypatch.setattr(transport, "public_addresses", lambda *a, **k: ["1.1.1.1"])
    assert (
        transport.PublicCaptureClient().fetch("https://example.org/", deadline=103).raw == b"hello"
    )
    assert observed and observed[0][0] <= observed[0][1] + 0.00001


@pytest.mark.parametrize(
    "tail", [b"<!-->not approved-->", b"<!--->not approved-->", b"<!--foo--!>"]
)
def test_malformed_comment_not_browser_repaired(tail):
    with pytest.raises(DomainError) as err:
        extract_static_text(b"<p>visible</p>" + tail, "text/html")
    assert err.value.code == "CAPTURE_HTML_MALFORMED"


def test_regular_comment_with_greater_than_still_hidden():
    assert extract_static_text(b"<p>visible</p><!--foo>bar-->", "text/html").body == b"visible\n"


@pytest.mark.parametrize("padding", [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009])
@pytest.mark.parametrize("bad", [b"<!-->bad-->", b"<!--->bad-->", b"<!--foo--!>"])
def test_bad_comment_split_across_feed_chunks(padding, bad):
    with pytest.raises(DomainError) as err:
        extract_static_text(b"<p>visible</p>" + b" " * padding + bad, "text/html")
    assert err.value.code == "CAPTURE_HTML_MALFORMED"


def test_valid_comment_single_trailing_hyphen_retained_policy():
    assert extract_static_text(b"<p>visible</p><!--foo--->", "text/html").body == b"visible\n"
