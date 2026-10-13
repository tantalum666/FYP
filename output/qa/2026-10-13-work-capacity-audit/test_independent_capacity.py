"""Independent retained-capacity adversarial audit; real isolated SQLite only."""

import hashlib
import json
from contextlib import contextmanager
from datetime import UTC, datetime
import pytest
from desk.runtime import Runtime
from desk.store import Store, DomainError
from desk.work_capacity import WorkCapacityService


@pytest.fixture
def world(tmp_path):
    runtime = Runtime(
        Store(
            tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 13, 12, tzinfo=UTC)
        )
    )
    token = runtime.store.authenticate("owner", "fixture-only")
    return runtime, hashlib.sha256(token.encode()).hexdigest()


def put(world, kind, raw, i=0):
    with world[0].store.connection(write=True) as c:
        c.execute(
            "INSERT INTO private_files VALUES(?,?,?,?,?,?,?)",
            (f"{i:032x}", kind, f"key-{i}", "unused", raw, "reserved", None),
        )


def get(world):
    return WorkCapacityService(world[0]).snapshot(session_hash=world[1])


@pytest.mark.parametrize(
    "raw",
    [
        '{"byte_count":1}\x00garbage',
        '{"byte_count":1}\x00',
        '{"byte_count":1,"\\u0062yte_count":9}',
        '{"byte_count":1,"byte_count":true}',
        '{"byte_count":1,"byte_count":' + json.dumps("x" * 70000) + "}",
        '{"byte_count":1,"ignored":' + json.dumps("界" * 22000, ensure_ascii=False) + "}",
        '{"byte_count":' + json.dumps("9" * 60000) + "}",
        '{"byte_count":' + ("9" * 60000) + "}",
    ],
)
def test_ambiguous_invalid_or_unbounded_metadata_is_unknown(world, raw):
    put(world, "sources", raw)
    r = get(world)
    assert r["sources"]["count"]["used"] == 1
    assert r["sources"]["bytes"]["state"] == "unavailable"
    assert r["sources"]["bytes"]["used"] is None
    assert r["artifacts"]["bytes"]["used"] == 0


@pytest.mark.parametrize("size", [65535, 65536, 65537])
def test_metadata_bound_is_utf8_bytes_and_inclusive(world, size):
    base = '{"byte_count":17,"unused":""}'
    raw = base[:-2] + ("x" * (size - len(base))) + base[-2:]
    assert len(raw.encode()) == size
    put(world, "artifacts", raw)
    r = get(world)["artifacts"]["bytes"]
    assert r["used"] == (17 if size <= 65536 else None)


@pytest.mark.parametrize("kind,cap", [("sources", 100), ("artifacts", 400)])
def test_cursor_materializes_only_bounded_single_scalar_rows(world, monkeypatch, kind, cap):
    for i in range(cap + 9):
        put(world, kind, '{"byte_count":1}', i)
    conn = world[0].store.connection
    selected = []

    class Proxy:
        def __init__(self, c):
            self.c = c

        def execute(self, sql, args=()):
            if "FROM private_files WHERE kind=" in sql:
                cursor = self.c.execute(sql, args)
                rows = cursor.fetchall()
                selected.append((args[0], len(rows)))
                assert len(rows) <= args[1]
                assert all(
                    len(row) == 1 and (row[0] is None or type(row[0]) is int) for row in rows
                )

                class Rows:
                    def fetchall(self):
                        return rows

                return Rows()
            return self.c.execute(sql, args)

    @contextmanager
    def connection(write=False):
        assert write is False
        with conn() as c:
            yield Proxy(c)

    monkeypatch.setattr(world[0].store, "connection", connection)
    r = get(world)
    assert (kind, cap + 1) in selected
    assert r[kind]["count"]["used"] is None and r[kind]["count"]["state"] == "over_limit"


@pytest.mark.parametrize("change", ["version", "epoch", "revoke"])
def test_final_new_transaction_blocks_authority_changes(world, monkeypatch, change):
    service = WorkCapacityService(world[0])
    original = service._read

    def read(c):
        result = original(c)
        with world[0].store.connection(write=True) as other:
            sql = {
                "version": "UPDATE settings SET version=version+1",
                "epoch": "UPDATE personal_settings SET epoch=epoch+1",
                "revoke": "DELETE FROM sessions",
            }[change]
            other.execute(sql)
        return result

    monkeypatch.setattr(service, "_read", read)
    with pytest.raises(DomainError) as error:
        service.snapshot(session_hash=world[1])
    assert error.value.code == (
        "OWNER_SIGN_IN_REQUIRED" if change == "revoke" else "WORK_CAPACITY_PRIVACY_CHANGED"
    )


@pytest.mark.parametrize(
    "raw",
    [
        '{"hide_private":false}\x00ignored',
        '{"hide_private":false,"hide_private":true}',
        '{"hide_private":0}',
        '{"hide_private":"false"}',
    ],
)
def test_corrupt_privacy_setting_fails_closed(world, raw):
    with world[0].store.connection(write=True) as c:
        c.execute("UPDATE settings SET data=?", (raw,))
    with pytest.raises(DomainError):
        get(world)
