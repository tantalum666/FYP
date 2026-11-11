"""One exact reviewed public HTTPS GET; strict static framing, local cleanup only.

The 16-KiB shared header guard conservatively includes buffered body read-ahead.
We additionally validate raw CRLF header syntax before http.client normalizes it.
No retry, redirect, proxy, ambient credentials, cookies or MCP notifications.
"""

from dataclasses import dataclass
import http.client
import ipaddress
import re
import socket
import time

from ..store import DomainError
from ..public_capture_policy import RAW_BYTES, validate_mime, validate_url
from .public_https import (
    PublicTransportError,
    _DeadlineSocket,
    _PinnedHTTPSConnection,
    public_addresses,
)

MAX_SECONDS = 20
HEADER_BYTES = 16384
_FIELD = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
_STATUS = re.compile(rb"HTTP/1\.[01] [0-9]{3}(?: [\x20-\x7e]*)?\r\n")


@dataclass(frozen=True)
class CaptureResponse:
    raw: bytes
    mime_type: str


def is_public_unicast(address):
    """Require every answer, including mapped forms, to be public unicast."""
    if not isinstance(address, str) or "%" in address:
        return False
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    # Python versions classify the IPv6 mapped envelope differently. The
    # actual endpoint is its embedded IPv4 address; apply every restriction to it.
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return is_public_unicast(str(mapped))
    if (
        not ip.is_global
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_reserved
    ):
        return False
    return True


class _CaptureHTTPSConnection(_PinnedHTTPSConnection):
    def __init__(self, host, address, timeout, *, deadline, checkpoint):
        super().__init__(host, address, timeout)
        self.deadline, self.checkpoint = deadline, checkpoint

    def connect(self):
        # Numeric socket.connect avoids create_connection's implicit second resolver
        # pass. There is exactly one endpoint and no alternate-address retry.
        family = socket.AF_INET6 if ":" in self.address else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            self.checkpoint()
            sock.settimeout(max(0.001, min(3, self.deadline - time.monotonic())))
            sock.connect((self.address, 443))
            self.checkpoint()
            sock.settimeout(max(0.001, min(3, self.deadline - time.monotonic())))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class _RawHeaderGuard:
    def __init__(self, fp):
        self.fp, self.first, self.done, self.count = fp, True, False, 0

    def __getattr__(self, name):
        return getattr(self.fp, name)

    def readline(self, limit=-1):
        line = self.fp.readline(min(HEADER_BYTES + 1, limit) if limit >= 0 else HEADER_BYTES + 1)
        if self.done:
            return line
        self.count += len(line)
        if self.count > HEADER_BYTES:
            raise DomainError("CAPTURE_HEADERS_LIMIT", 502)
        if not line.endswith(b"\r\n"):
            raise DomainError("CAPTURE_FRAMING_INVALID", 502)
        if self.first:
            self.first = False
            if not _STATUS.fullmatch(line):
                raise DomainError("CAPTURE_FRAMING_INVALID", 502)
        elif line == b"\r\n":
            self.done = True
        else:
            name, colon, value = line[:-2].partition(b":")
            if (
                not colon
                or not _FIELD.fullmatch(name)
                or any(byte < 32 and byte != 9 or byte == 127 for byte in value)
            ):
                raise DomainError("CAPTURE_FRAMING_INVALID", 502)
        return line


class _CaptureHTTPResponse(http.client.HTTPResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fp = _RawHeaderGuard(self.fp)

    def _read_status(self):
        version, status, reason = super()._read_status()
        if 100 <= status < 200:
            raise DomainError("CAPTURE_INTERIM_DENIED", 502)
        return version, status, reason

    def begin(self):
        try:
            super().begin()
            if self.headers.defects:
                raise DomainError("CAPTURE_FRAMING_INVALID", 502)
        except BaseException:
            # getresponse() has not returned a response to the caller yet.
            self.close()
            raise


def _single(headers, name, *, required=False):
    values = headers.get_all(name, [])
    if len(values) > 1 or required and len(values) != 1:
        raise DomainError("CAPTURE_FRAMING_INVALID", 502)
    return values[0] if values else None


class PublicCaptureClient:
    """Internal transport. Durable reviewed authority belongs to its caller."""

    def _connection(self, host, deadline, checkpoint):
        addresses = public_addresses(host, deadline=deadline, checkpoint=checkpoint)
        if any(not is_public_unicast(address) for address in addresses):
            raise DomainError("CAPTURE_PUBLIC_DNS_REQUIRED", 403)
        checkpoint()
        return _CaptureHTTPSConnection(
            host,
            addresses[0],
            max(0.001, min(3, deadline - time.monotonic())),
            deadline=deadline,
            checkpoint=checkpoint,
        )

    def fetch(self, url, checkpoint=lambda: None, *, on_dispatch=None, deadline=None):
        target = validate_url(url)
        deadline = (
            min(deadline, time.monotonic() + MAX_SECONDS)
            if deadline is not None
            else (time.monotonic() + MAX_SECONDS)
        )

        def check():
            checkpoint()
            if time.monotonic() >= deadline:
                raise DomainError("CAPTURE_DEADLINE", 504)

        conn, response, wrapped = None, None, None
        try:
            check()
            conn = self._connection(target.host, deadline, check)
            check()
            conn.timeout = max(0.001, min(3, deadline - time.monotonic()))
            conn.connect()
            check()
            wrapped = _DeadlineSocket(conn.sock, deadline, check)
            conn.sock = wrapped
            conn.response_class = _CaptureHTTPResponse
            if on_dispatch:
                on_dispatch()
            check()
            # TLS and durable dispatch can consume most of the remaining budget.
            # The subsequent blocking send must not keep the earlier phase timeout.
            conn.sock.settimeout(max(0.001, min(3, deadline - time.monotonic())))
            conn.request(
                "GET",
                target.path,
                headers={
                    "Accept": "text/plain, text/markdown, text/html",
                    "Accept-Encoding": "identity",
                    "User-Agent": "DeskCompanion-PublicCapture/1",
                    "Connection": "close",
                },
            )
            response = conn.getresponse()
            wrapped.header_phase = False
            check()
            if response.status in (401, 403):
                raise DomainError("CAPTURE_AUTH_REQUIRED", 403)
            if 300 <= response.status < 400:
                raise DomainError("CAPTURE_REDIRECT_DENIED", 502)
            if response.status != 200:
                raise DomainError("CAPTURE_HTTP_ERROR", 502)
            headers = response.headers
            if headers.get_all("Transfer-Encoding") or headers.get_all("Upgrade"):
                raise DomainError("CAPTURE_FRAMING_INVALID", 502)
            length = _single(headers, "Content-Length", required=True)
            if not re.fullmatch(r"[1-9][0-9]{0,5}", length) or int(length) > RAW_BYTES:
                raise DomainError("CAPTURE_RESPONSE_LIMIT", 502)
            encoding = _single(headers, "Content-Encoding")
            if encoding is not None and encoding.lower() != "identity":
                raise DomainError("CAPTURE_ENCODING_DENIED", 502)
            mime = validate_mime(_single(headers, "Content-Type", required=True))
            raw = bytearray()
            expected = int(length)
            while len(raw) < expected:
                check()
                chunk = response.read1(min(4096, expected - len(raw)))
                check()
                if not chunk:
                    raise DomainError("CAPTURE_BODY_INCOMPLETE", 502)
                raw.extend(chunk)
            check()
            return CaptureResponse(bytes(raw), mime)
        except PublicTransportError as error:
            raise DomainError("CAPTURE_" + error.code, error.status) from None
        except (OSError, http.client.HTTPException):
            raise DomainError("CAPTURE_TRANSPORT_FAILED", 502) from None
        finally:
            if response is not None:
                response.close()
            if conn is not None:
                conn.close()
            if wrapped is not None:
                wrapped.close()
