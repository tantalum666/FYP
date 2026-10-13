#!/usr/bin/env python3
"""Offline-only wrapper around the existing real-loopback acceptance test.

No live mode: actual public acceptance requires the separate authorized UI flow.
No production implementation or transport-policy changes are made by this file.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True, help='New evidence directory only')
args = parser.parse_args()
repo = args.repo.resolve()
out = args.output.resolve()
if out.exists():
    parser.error('Output must not already exist; no evidence overwrite')
network = []

def network_guard(event, values):
    if event not in {'socket.connect', 'socket.getaddrinfo'}:
        return
    target = values[1] if event == 'socket.connect' else values[0]
    host = target[0] if isinstance(target, tuple) else target
    try:
        allowed = ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        allowed = False
    network.append({'event': event, 'host': str(host), 'allowed_loopback': allowed})
    if not allowed:
        raise RuntimeError('OFFLINE_ONLY: non-loopback connection or DNS forbidden')

sys.addaudithook(network_guard)
sys.dont_write_bytecode = True
sys.path[:0] = [str(repo / 'desk-companion/backend'), str(repo / 'desk-companion/tests')]
from test_public_captures import world, test_actual_loopback_get_explicit_deterministic_work  # noqa: E402 - install network guard before application imports

out.mkdir(parents=True)

def save(name, value):
    (out / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

observed = {'reviews': [], 'approvals': [], 'sources': [], 'artifacts': [], 'work': None}
with tempfile.TemporaryDirectory(prefix='fyp-capture-offline-') as scratch:
    w = world.__wrapped__(Path(scratch))
    runtime, session = w[:2]
    original_prepare = w[4].prepare
    original_approve = w[4].approve
    original_read = runtime.sources.read_all
    original_download = runtime.artifacts.download
    original_detail = runtime.agent_runs.detail

    def prepare(*a, **kw):
        value = original_prepare(*a, **kw)
        observed['reviews'].append(value)
        return value

    def approve(*a, **kw):
        value = original_approve(*a, **kw)
        observed['approvals'].append(value)
        return value

    def read(*a, **kw):
        value = original_read(*a, **kw)
        body = value['content'].encode()
        assert hashlib.sha256(body).hexdigest() == value['sha256']
        (out / 'source.txt').write_bytes(body)
        assert (out / 'source.txt').read_bytes() == body
        observed['sources'].append(value)
        return value

    def download(*a, **kw):
        record, body = original_download(*a, **kw)
        name = 'report.md' if record['format'] == 'markdown' else 'evidence.csv'
        (out / name).write_bytes(body)
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == record['sha256']
        observed['artifacts'].append({'file': name, 'metadata': record})
        return record, body

    def detail(*a, **kw):
        value = original_detail(*a, **kw)
        run = value['run']
        observed['work'] = {key: run.get(key) for key in
                            ('id', 'state', 'mode', 'model_calls', 'source_ids')}
        return value

    w[4].prepare, w[4].approve = prepare, approve
    runtime.sources.read_all, runtime.artifacts.download = read, download
    runtime.agent_runs.detail = detail
    try:
        test_actual_loopback_get_explicit_deterministic_work(w)
        observed['capture'] = w[4].listing(session_hash=session)['captures'][0]
        assert len(observed['artifacts']) == 2
        assert observed['work']['state'] == 'succeeded'
        assert observed['work']['model_calls'] == 0
        save('evidence.json', observed)
        save('result.json', {
            'status': 'passed_offline_only',
            'recorded_utc': datetime.now(timezone.utc).isoformat(),
            'test': 'test_actual_loopback_get_explicit_deterministic_work',
            'network_events': network,
            'public_requests': 0,
            'live_dns_tls': 'not_tested',
            'mounted_ui': 'not_tested',
            'browser_saved_downloads': 'not_tested',
            'model_quality': 'not_tested',
            'source_content': 'synthetic_test_fixture',
            'runtime': 'new_temporary_synthetic_store_removed_on_exit',
        })
    finally:
        w[4].stop()
        runtime.agent_runs.shutdown()
print('PASS: offline loopback, explicit synthetic review, source and two actual artifact readbacks; public/UI acceptance remains pending')
