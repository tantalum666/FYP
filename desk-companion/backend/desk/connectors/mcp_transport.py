"""Bounded MCP 2025-11-25 tools over Streamable HTTP, without credentials.

Production connections pin a validated public DNS address while retaining the
original TLS hostname/certificate check. No subprocess, proxy, cookies, redirects,
ambient auth, SDK callbacks, roots, sampling, elicitation, tasks or reconnection.
"""

import http.client
import socket as socket  # compatibility for existing test seams
import ssl as ssl  # compatibility for existing test seams
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

from .contracts import PROTOCOL_VERSION, validate_endpoint
from .schema import ConnectorError, canonical, check_schema, digest, parse_json

MAX_RESPONSE = 131072
MAX_REQUEST = 32768
MAX_SECONDS = 20


# Compatibility names remain available to existing callers and test seams.
from .public_https import (  # noqa: E402
    _DNS_SLOT as _DNS_SLOT,
    _PinnedHTTPSConnection as _PinnedHTTPSConnection,
    _DeadlineReader as _DeadlineReader,
    _DeadlineSocket as _SharedDeadlineSocket,
    PublicTransportError,
    public_addresses as _shared_public_addresses,
)


def public_addresses(host, *, deadline=None, checkpoint=lambda: None):
    try:
        return _shared_public_addresses(
            host,
            deadline=deadline if deadline is not None else time.monotonic() + MAX_SECONDS,
            checkpoint=checkpoint,
        )
    except PublicTransportError as error:
        raise ConnectorError("CONNECTOR_" + error.code, error.status) from None


class _DeadlineSocket(_SharedDeadlineSocket):
    def makefile(self, mode):
        try:
            return super().makefile(mode)
        except PublicTransportError as error:
            raise ConnectorError("CONNECTOR_" + error.code, error.status) from None


class McpHttpClient:
    def __init__(self, config):
        self.config = config
        self.endpoint = validate_endpoint(config.endpoint)
        self.url = urlsplit(self.endpoint)
        self.session_id = None
        self.initialized = False
        self.catalog_changed = False
        self.server_info = None
        self.identity_verified = False

    def _connection(self):
        # This seam is overridden only by local test code; no runtime fixture flag.
        address = public_addresses(
            self.url.hostname, deadline=self._deadline, checkpoint=self._network_checkpoint
        )[0]
        return _PinnedHTTPSConnection(
            self.url.hostname,
            address,
            timeout=max(0.001, min(3, self._deadline - time.monotonic())),
        )

    @staticmethod
    def _check(checkpoint, deadline):
        checkpoint()
        if time.monotonic() >= deadline:
            raise ConnectorError("CONNECTOR_DEADLINE", 504)

    def _exchange(self, message, checkpoint, *, notification=False, on_dispatch=None):
        body = canonical(message, limit=MAX_REQUEST)
        deadline = time.monotonic() + MAX_SECONDS
        self._check(checkpoint, deadline)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "identity",
            "User-Agent": "DeskCompanion-MCP/1",
            "Connection": "close",
        }
        if self.initialized:
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        self._deadline = deadline
        self._network_checkpoint = checkpoint
        conn = self._connection()
        response = None
        try:
            # Resolve/connect first: failed TLS/DNS is known before tool dispatch.
            conn.timeout = max(0.001, min(3, deadline - time.monotonic()))
            conn.connect()
            self._check(checkpoint, deadline)
            wrapped = _DeadlineSocket(
                conn.sock, deadline, lambda: self._check(checkpoint, deadline)
            )
            conn.sock = wrapped
            if on_dispatch:
                on_dispatch()  # Host commits once-only ledger immediately before possible send.
            self._check(checkpoint, deadline)
            conn.request("POST", self.url.path, body=body, headers=headers)
            response = conn.getresponse()
            wrapped.header_phase = False
            self._check(checkpoint, deadline)
            if sum(len(k) + len(v) for k, v in response.getheaders()) > 16384:
                raise ConnectorError("CONNECTOR_HEADERS_LIMIT", 502)
            if response.status in (401, 403):
                raise ConnectorError("CONNECTOR_AUTH_REQUIRED", 403)
            if 300 <= response.status < 400:
                raise ConnectorError("CONNECTOR_REDIRECT_DENIED", 502)
            if response.status == 404 and self.session_id:
                # A future fresh preparation can negotiate a new session. Never replay a call.
                raise ConnectorError("CONNECTOR_SESSION_EXPIRED", 409)
            if notification:
                if response.status != 202:
                    raise ConnectorError("CONNECTOR_NOTIFICATION_REJECTED", 502)
                return None
            if response.status != 200:
                raise ConnectorError("CONNECTOR_HTTP_ERROR", 502)
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise ConnectorError("CONNECTOR_ENCODING_DENIED", 502)
            size = response.getheader("Content-Length")
            if size is not None and (not size.isdigit() or int(size) > MAX_RESPONSE):
                raise ConnectorError("CONNECTOR_RESPONSE_LIMIT", 502)
            if message.get("method") == "initialize":
                session = response.getheader("MCP-Session-Id")
                if session:
                    if len(session) > 256 or any(not 0x21 <= ord(c) <= 0x7E for c in session):
                        raise ConnectorError("CONNECTOR_SESSION_INVALID", 502)
                    self.session_id = session
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in {"application/json", "text/event-stream"}:
                raise ConnectorError("CONNECTOR_CONTENT_TYPE", 502)
            raw, buffer = bytearray(), bytearray()
            events = 0
            while True:
                self._check(checkpoint, deadline)
                if conn.sock:
                    conn.sock.settimeout(max(0.01, min(3, deadline - time.monotonic())))
                chunk = response.read1(4096)
                self._check(checkpoint, deadline)
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_RESPONSE:
                    raise ConnectorError("CONNECTOR_RESPONSE_LIMIT", 502)
                if content_type == "text/event-stream":
                    buffer.extend(chunk)
                    normalized = bytes(buffer).replace(b"\r\n", b"\n")
                    while b"\n\n" in normalized:
                        event, normalized = normalized.split(b"\n\n", 1)
                        events += 1
                        if events > 128:
                            raise ConnectorError("CONNECTOR_EVENT_LIMIT", 502)
                        lines = [
                            line[5:].lstrip(b" ")
                            for line in event.split(b"\n")
                            if line.startswith(b"data:")
                        ]
                        if lines and b"\n".join(lines):
                            value = parse_json(b"\n".join(lines))
                            result = self._message(value, message["id"], allow_notifications=True)
                            if result is not None:
                                return result
                    buffer = bytearray(normalized)
            if content_type == "text/event-stream":
                raise ConnectorError("CONNECTOR_STREAM_INCOMPLETE", 502)
            return self._message(parse_json(bytes(raw)), message["id"])
        except PublicTransportError as error:
            raise ConnectorError("CONNECTOR_" + error.code, error.status) from None
        except (OSError, http.client.HTTPException):
            raise ConnectorError("CONNECTOR_TRANSPORT_FAILED", 502) from None
        finally:
            if response is not None:
                response.close()
            conn.close()

    def _message(self, value, request_id, allow_notifications=False):
        if type(value) is not dict or value.get("jsonrpc") != "2.0":
            raise ConnectorError("CONNECTOR_PROTOCOL_INVALID", 502)
        if "method" in value:
            if "id" in value:
                # No server-to-client permissions or tools are advertised or fulfilled.
                raise ConnectorError("CONNECTOR_SERVER_REQUEST_DENIED", 502)
            if allow_notifications and value.get("method") == "notifications/progress":
                return None
            if value.get("method") == "notifications/tools/list_changed":
                self.catalog_changed = True
                raise ConnectorError("CONNECTOR_CATALOG_CHANGED", 409)
            raise ConnectorError("CONNECTOR_NOTIFICATION_UNSUPPORTED", 502)
        if type(value.get("id")) is not str or value["id"] != request_id:
            raise ConnectorError("CONNECTOR_RESPONSE_ID", 502)
        if ("result" in value) == ("error" in value):
            raise ConnectorError("CONNECTOR_PROTOCOL_INVALID", 502)
        if "error" in value:
            # Do not echo potentially private/error-injected server text into logs.
            raise ConnectorError("CONNECTOR_RPC_ERROR", 502)
        if type(value["result"]) is not dict:
            raise ConnectorError("CONNECTOR_PROTOCOL_INVALID", 502)
        return value["result"]

    def request(self, method, params, checkpoint=lambda: None, *, on_dispatch=None):
        request_id = uuid4().hex
        dispatched = [False]

        def sent():
            if on_dispatch:
                on_dispatch()
            dispatched[0] = True

        try:
            return self._exchange(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                checkpoint,
                on_dispatch=sent,
            )
        except Exception:
            if dispatched[0] and method != "initialize":
                self.cancel_request(request_id)
            raise

    def cancel_request(self, request_id):
        try:
            self._exchange(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/cancelled",
                    "params": {"requestId": request_id, "reason": "Client stopped waiting"},
                },
                lambda: None,
                notification=True,
            )
        except Exception:
            pass  # Cancellation is best effort, never rollback or proof of no effect.

    def initialize(self, checkpoint=lambda: None, *, verify_identity=True):
        result = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "DeskCompanion", "version": "1"},
            },
            checkpoint,
        )
        info, capabilities = result.get("serverInfo"), result.get("capabilities")
        if (
            result.get("protocolVersion") != PROTOCOL_VERSION
            or type(info) is not dict
            or type(info.get("name")) is not str
            or not 1 <= len(info["name"]) <= 128
            or type(info.get("version")) is not str
            or not 1 <= len(info["version"]) <= 128
            or (
                verify_identity
                and (
                    info["name"] != self.config.server_name
                    or info["version"] != self.config.server_version
                )
            )
            or type(capabilities) is not dict
            or type(capabilities.get("tools")) is not dict
        ):
            raise ConnectorError("CONNECTOR_SERVER_CHANGED", 409)
        self.server_info = {"name": info["name"], "version": info["version"]}
        self.identity_verified = verify_identity
        self.initialized = True
        self._exchange(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, checkpoint, notification=True
        )

    def discover(self, checkpoint=lambda: None, *, verify_identity=True):
        self.initialize(checkpoint, verify_identity=verify_identity)
        tools, cursors, params = {}, set(), {}
        for _ in range(4):
            result = self.request("tools/list", params, checkpoint)
            page = result.get("tools")
            if type(page) is not list or len(page) > 64:
                raise ConnectorError("CONNECTOR_CATALOG_LIMIT", 502)
            for descriptor in page:
                if type(descriptor) is not dict:
                    raise ConnectorError("CONNECTOR_CATALOG_INVALID", 502)
                name = descriptor.get("name")
                if (
                    type(name) is not str
                    or not name
                    or len(name) > 128
                    or name in tools
                    or len(tools) >= 64
                ):
                    raise ConnectorError("CONNECTOR_CATALOG_INVALID", 502)
                canonical(descriptor, limit=16384)
                # Discovery includes unsupported schemas so operators can inspect them;
                # admission at prepare/call fails closed, never silently drops constraints.
                tools[name] = {"descriptor": descriptor, "descriptor_sha256": digest(descriptor)}
            cursor = result.get("nextCursor")
            if cursor is None:
                return tools
            if type(cursor) is not str or not cursor or len(cursor) > 512 or cursor in cursors:
                raise ConnectorError("CONNECTOR_CURSOR_INVALID", 502)
            cursors.add(cursor)
            params = {"cursor": cursor}
        raise ConnectorError("CONNECTOR_CATALOG_LIMIT", 502)

    def call(self, name, arguments, descriptor, checkpoint, on_dispatch):
        if not self.initialized or not self.identity_verified or self.catalog_changed:
            raise ConnectorError("CONNECTOR_CATALOG_REQUIRED", 409)
        if descriptor.get("execution", {}).get("taskSupport") == "required":
            raise ConnectorError("CONNECTOR_TASKS_UNSUPPORTED", 422)
        check_schema(descriptor.get("inputSchema"))
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments},
            checkpoint,
            on_dispatch=on_dispatch,
        )
        return result


def inspect_endpoint(endpoint, checkpoint=lambda: None):
    """Operator-only read-only metadata inspection; never yields an executable client/grant."""
    client = McpHttpClient(SimpleNamespace(endpoint=endpoint, server_name="", server_version=""))
    tools = client.discover(checkpoint, verify_identity=False)
    return {
        "endpoint": endpoint,
        "server_info": client.server_info,
        "server_sha256": digest(client.server_info),
        "tools": tools,
        "trusted": False,
    }
