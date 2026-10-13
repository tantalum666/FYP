import http.client
import socket
import threading
import time
from types import SimpleNamespace

import pytest
from desk.connectors.schema import ConnectorError, canonical, digest
from desk.connectors.service import McpConnectorService
from desk.connectors.mcp_transport import McpHttpClient
import desk.connectors.mcp_transport as transport
from test_mcp_connectors import world as world, server as server, ARGS, DESCRIPTOR


def test_result_at_parser_node_limit_does_not_wedge_dispatching(world):
    runtime, _, owner, config, state, clock, factory = world
    descriptor = {k: v for k, v in DESCRIPTOR.items() if k != 'outputSchema'}
    result = {'content': [], 'structuredContent': {f'p{i}': [0] * 126 for i in range(32)}}
    canonical(result, limit=65536)
    class NodeClient:
        def __init__(self, config): pass
        def discover(self, checkpoint):
            checkpoint()
            return {'notes.create': {'descriptor': descriptor, 'descriptor_sha256': digest(descriptor)}}
        def call(self, name, arguments, descriptor, checkpoint, on_dispatch):
            on_dispatch()
            return result
    config.tools[0].descriptor_sha256 = digest(descriptor)
    service = McpConnectorService(runtime, [config], client_factory=NodeClient)
    runtime.connectors = service
    item = service.prepare('mcp.fixture.notes.create', ARGS, 'node-limit', owner, public_only=True)
    service.approve(item['id'], item['version'], item['intent_hash'], owner, public_only=True)
    error = None
    try:
        service.execute(item['id'])
    except ConnectorError as exc:
        error = exc.code
    current = service.detail(item['id'], owner)
    print('RESULT_NODE_LIMIT', {'exception': error, 'state': current['state'], 'dispatched': current['dispatched'], 'advance': service.advance_one()})
    assert current['state'] != 'dispatching', (error, current['state'])


def test_slow_headers_respect_absolute_deadline(monkeypatch):
    # Local raw HTTP seam only; no external connection, TLS or credentials.
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen()
    port = listener.getsockname()[1]
    def serve():
        conn, _ = listener.accept()
        try:
            conn.recv(4096)
            for byte in b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}':
                conn.sendall(bytes([byte]))
                time.sleep(.01)
        except OSError:
            pass
        finally:
            conn.close()
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    class LocalClient(McpHttpClient):
        def _connection(self):
            return http.client.HTTPConnection('127.0.0.1', port, timeout=1)
    monkeypatch.setattr(transport, 'MAX_SECONDS', .05)
    client = LocalClient(SimpleNamespace(endpoint='https://fixture.example/mcp'))
    start = time.monotonic()
    try:
        with pytest.raises(ConnectorError) as exc:
            client.request('initialize', {})
        elapsed = time.monotonic() - start
        print('SLOW_HEADERS', {'deadline': .05, 'elapsed': elapsed, 'error': exc.value.code})
        assert elapsed < .25
    finally:
        listener.close()
        thread.join(2)


def test_blocked_dns_is_bounded_and_late_resolution_cannot_connect(monkeypatch):
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def resolve(*args, **kwargs):
        entered.set()
        release.wait(2)
        completed.set()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    monkeypatch.setattr(transport, 'MAX_SECONDS', .05)
    monkeypatch.setattr(transport, '_PinnedHTTPSConnection', lambda *a, **kw: calls.append('connection'))
    client = McpHttpClient(SimpleNamespace(endpoint='https://fixture.example/mcp'))
    try:
        start = time.monotonic()
        with pytest.raises(ConnectorError) as exc:
            client.request('initialize', {})
        elapsed = time.monotonic() - start
        assert exc.value.code == 'CONNECTOR_DEADLINE'
        assert entered.is_set() and elapsed < .25
        with pytest.raises(ConnectorError) as busy:
            transport.public_addresses('fixture.example')
        assert busy.value.code == 'CONNECTOR_RESOLVER_BUSY'
        assert calls == []
        release.set()
        assert completed.wait(1)
        time.sleep(.03)
        assert calls == []
        print('BOUNDED_DNS', {'elapsed': elapsed, 'late_connections': len(calls), 'busy_error': busy.value.code})
    finally:
        release.set()
        completed.wait(2)
