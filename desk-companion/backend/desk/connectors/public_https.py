"""Shared pinned TLS, one bounded DNS slot, and conservative buffered read guards.

MCP admission intentionally retains its historical is_global semantics. Capture
adds explicit public-unicast admission without changing the MCP protocol.
"""

import http.client
import ipaddress
import io
import socket
import ssl
import time
import threading


class PublicTransportError(Exception):
    def __init__(self, code, status=502):
        self.code, self.status = code, status
        super().__init__(code)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, 443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


_DNS_SLOT = threading.BoundedSemaphore(1)


def public_addresses(host, *, deadline=None, checkpoint=lambda: None):
    """One resolver may outlive a caller; no unbounded blocked resolver/thread queue."""
    deadline = deadline if deadline is not None else time.monotonic() + 20
    if not _DNS_SLOT.acquire(blocking=False):
        raise PublicTransportError("RESOLVER_BUSY", 503)
    complete, values = threading.Event(), []

    def resolve():
        try:
            values.append(socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM))
        except OSError:
            values.append(None)
        finally:
            _DNS_SLOT.release()
            complete.set()

    threading.Thread(target=resolve, name="connector-dns", daemon=True).start()
    while not complete.wait(0.02):
        checkpoint()
        if time.monotonic() >= deadline:
            raise PublicTransportError("DEADLINE", 504)
    checkpoint()
    if time.monotonic() >= deadline:
        raise PublicTransportError("DEADLINE", 504)
    try:
        addresses = sorted({entry[4][0] for entry in values[0]})
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise ValueError()
    except (TypeError, ValueError):
        raise PublicTransportError("PUBLIC_DNS_REQUIRED", 403) from None
    return addresses


class _DeadlineReader(io.RawIOBase):
    def __init__(self, wrapper):
        self.wrapper = wrapper
        wrapper.readers += 1

    def readable(self):
        return True

    def readinto(self, buffer):
        wrapper = self.wrapper
        wrapper.check()
        wrapper.socket.settimeout(max(0.001, min(3, wrapper.deadline - time.monotonic())))
        count = wrapper.socket.recv_into(buffer)
        wrapper.check()
        if wrapper.header_phase:
            wrapper.header_bytes += count
            if wrapper.header_bytes > 16384:
                raise PublicTransportError("HEADERS_LIMIT", 502)
        return count

    def close(self):
        if not self.closed:
            self.wrapper.readers -= 1
            self.wrapper.finish_close()
        super().close()


class _DeadlineSocket:
    """http.client's header parser and body reads share the same total deadline."""

    def __init__(self, sock, deadline, check):
        self.socket, self.deadline, self.check = sock, deadline, check
        self.readers, self.closing, self.header_bytes, self.header_phase = 0, False, 0, True

    def __getattr__(self, name):
        return getattr(self.socket, name)

    def makefile(self, mode):
        if mode != "rb":
            raise PublicTransportError("TRANSPORT_INVALID", 502)
        return io.BufferedReader(_DeadlineReader(self), buffer_size=4096)

    def close(self):
        self.closing = True
        self.finish_close()

    def finish_close(self):
        if self.closing and self.readers == 0:
            self.socket.close()
