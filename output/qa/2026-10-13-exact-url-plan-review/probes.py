"""Offline review probes; no DNS/network call, credentials, or runtime database."""
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from desk.connectors.mcp_transport import public_addresses
from desk.file_store import ImmutableFiles
from desk.store import DomainError

results = {}
for address in ('224.0.0.1', 'ff02::1'):
    family = socket.AF_INET6 if ':' in address else socket.AF_INET
    answer = [(family, socket.SOCK_STREAM, 6, '', (address, 443))]
    with patch('desk.connectors.mcp_transport.socket.getaddrinfo', return_value=answer):
        results['existing_dns_' + address] = public_addresses('fixture.example')

class FakeSocket:
    def __init__(self, raw):
        self.raw = raw
    def makefile(self, mode):
        return io.BytesIO(self.raw)

response = http.client.HTTPResponse(FakeSocket(
    b'HTTP/1.1 100 Continue\r\nX-Interim: discarded\r\n\r\n'
    b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nContent-Type: text/plain\r\n\r\nok'))
response.begin()
results['default_response_interim'] = {
    'status': response.status, 'headers': response.getheaders(), 'body': response.read().decode()
}
response.close()

with tempfile.TemporaryDirectory(prefix='fyp-capture-review-') as root:
    folder = Path(root, 'sources')
    folder.mkdir(mode=0o700)
    file_id = 'a' * 32
    pending = folder / ('.' + file_id + '.pending')
    final = folder / (file_id + '.txt')
    body = b'fictional fixture\n'
    pending.write_bytes(body)
    pending.chmod(0o600)
    os.link(pending, final)
    files = object.__new__(ImmutableFiles)
    files.store = SimpleNamespace(directory=Path(root))
    row = {'id': file_id, 'kind': 'sources', 'format': 'text', 'status': 'reserved',
           'byte_count': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    try:
        files._read_bytes(row)
    except DomainError as error:
        results['linked_pending_retained'] = {'nlink': final.stat().st_nlink, 'error': error.code}
    pending.unlink()  # Fixture setup of the distinct later crash window, not a recovery action.
    results['after_pending_unlinked'] = {'nlink': final.stat().st_nlink,
                                        'exact_readback': files._read_bytes(row) == body}
print(json.dumps(results, indent=2))
