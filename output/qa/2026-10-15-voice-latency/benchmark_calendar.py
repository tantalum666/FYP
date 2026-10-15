"""Offline real-calendar-tool timings on synthetic SQLite fixtures, not a voice SLA."""
import asyncio
import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace

QA = Path(__file__).resolve().parent
ROOT = QA.parents[2]
sys.path.insert(0, str(ROOT / 'desk-companion/backend'))
os.environ['DESK_VOICE_PROVIDER'] = 'none'
os.environ['DESK_TEXT_PROVIDER'] = 'none'
os.environ['DESK_COMPUTER_ENABLED'] = '0'
from desk.assistant import AssistantService
from desk.schemas import EventInput, SettingsInput
from desk.store import Store, encode
from desk.tool_dispatch import ToolDispatcher

BEGIN = datetime.fromisoformat('2026-10-19T00:00:00+08:00')
END = datetime.fromisoformat('2026-10-26T00:00:00+08:00')
QUERY = {'start': BEGIN.isoformat(), 'end': END.isoformat()}

def seed(store, count):
    rows = []
    for i in range(count):
        recurrence = {'frequency': 'none'}
        if i < 7:
            start = datetime(2026, 10, 19, 10) + timedelta(days=i)
        elif i < 12:
            start = datetime(2026, 9, 7, 11) + timedelta(days=i-7)
            recurrence = {'frequency': 'weekly'}
        elif i < 15:
            start = datetime(2026, 9, 1, 12+i-12)
            recurrence = {'frequency': 'daily'}
        else:
            start = datetime(2020, 1, 1, 9) + timedelta(days=i)
        private = i % 2 == 0
        event = EventInput(title=('FIXTURE_PRIVATE_' if private else 'Fixture meeting ') + str(i), start_local=start, end_local=start+timedelta(minutes=30), visibility='private' if private else 'displayable', recurrence=recurrence, reminder_minutes=[])
        doc = event.model_dump(mode='json')
        doc.update(origin='qa_fixture', batch_id=None, provider=None, external_id=None)
        rows.append((f'fixture-{i}', encode(doc)))
    with store.connection(write=True) as conn:
        conn.executemany('INSERT INTO events(id,data,version) VALUES(?,?,1)', rows)
        store.bump(conn)

async def measure(service, count, samples=100):
    timings = []
    first_ms = None
    payload_bytes = None
    runtime = SimpleNamespace(assistant=service)
    for i in range(samples):
        dispatcher = ToolDispatcher(runtime, f'latency-{count}-{i}')
        before = perf_counter()
        dispatcher.submit({'type': 'tool', 'id': f'query-{i}', 'name': 'calendar_query', 'arguments': QUERY})
        event, result = await asyncio.wait_for(dispatcher.results.get(), timeout=3)
        payload = json.dumps(result, ensure_ascii=False).encode()
        elapsed_ms = (perf_counter()-before)*1000
        timings.append(elapsed_ms)
        if first_ms is None:
            first_ms = elapsed_ms
            payload_bytes = len(payload)
        assert 'error' not in result, result
        assert result['timezone'] == 'Asia/Hong_Kong'
        assert len(result['occurrences']) == 33, len(result['occurrences'])
        assert all(BEGIN <= datetime.fromisoformat(o['start'].replace('Z', '+00:00')) < END for o in result['occurrences'])
        dispatcher.delivered(event['id'], result)
        await dispatcher.close()
    ordered = sorted(timings)
    return {'total_event_rows': count, 'samples': samples, 'returned_occurrences': 33, 'serialized_bytes': payload_bytes, 'first_measured_ms': round(first_ms, 3), 'p50_ms': round(ordered[math.ceil(.50*samples)-1], 3), 'p95_ms': round(ordered[math.ceil(.95*samples)-1], 3), 'maximum_ms': round(max(timings), 3)}

async def main():
    results = []
    for count in (100, 500):
        with TemporaryDirectory(prefix='fyp-voice-latency-') as directory:
            store = Store(Path(directory), password='fixture-only', clock=lambda: datetime(2026, 10, 15, 4, tzinfo=UTC))
            seed(store, count)
            service = AssistantService(SimpleNamespace(store=store))
            row = await measure(service, count)
            store.update_settings(SettingsInput(expected_version=1, hide_private=True, timezone='Asia/Hong_Kong'), 'privacy-check')
            redacted = service.tool('calendar_query', QUERY, 'privacy-read')
            assert 'FIXTURE_PRIVATE_' not in json.dumps(redacted)
            row['privacy_projection_checked'] = True
            results.append(row)
    record = {'date': '2026-10-15', 'source_base': '9e371ffd095b78832ef4ada6f2b4f4905b174fc5', 'environment': {'platform': platform.platform(), 'python': platform.python_version()}, 'measured_path': 'ToolDispatcher.submit -> asyncio.to_thread -> AssistantService.calendar_query -> Store.snapshot -> recurrence expansion/privacy projection -> JSON serialization', 'fixture': '100/500 validated synthetic events, including daily/weekly recurrence; current application cap is 500. Direct fixture seeding is excluded from timing.', 'excluded': ['microphone', 'speech end detection', 'provider connection', 'network', 'model inference', 'speech synthesis', 'browser playback', 'real calendar data', 'contended tool slots or database writers'], 'limits': 'Repeated local process samples after fixture seeding; first_measured is not an OS cold boot or a live voice response. No paid calls or runtime workers.', 'results': results}
    (QA/'calendar-tool-timings.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))

asyncio.run(main())
