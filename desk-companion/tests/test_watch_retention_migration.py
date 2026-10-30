"""Migration opt-in and rollback on synthetic SQLite databases only."""

import sqlite3
from contextlib import closing, contextmanager

import pytest

from desk.responsibility_retention import RETENTION_COLUMNS, WATCH_TABLES
from desk.store import DomainError, Store
from test_responsibilities import control, enroll, task, world as watch_world


def legacy_runtime(tmp_path):
    world = watch_world.__wrapped__(tmp_path)
    watch = control(world, enroll(world, [task(world)]), "cancel")
    store = world[0].store
    with store.connection(write=True) as conn:
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'responsibility_%'"
        ).fetchall():
            conn.execute(f"DROP TRIGGER {row[0]}")
        conn.execute("DROP INDEX responsibilities_retained")
        conn.execute("DROP INDEX responsibilities_charged")
        for name in RETENTION_COLUMNS:
            conn.execute(f"ALTER TABLE responsibilities DROP COLUMN {name}")
        for operation, source in (("INSERT", "NEW"), ("UPDATE", "NEW"), ("DELETE", "OLD")):
            conn.execute(f"""CREATE TRIGGER responsibility_task_{operation.lower()}
                AFTER {operation} ON tasks BEGIN UPDATE responsibility_sources
                SET dirty_generation=dirty_generation+1 WHERE source_id={source}.id AND responsibility_id IN
                (SELECT id FROM responsibilities WHERE status IN ('active','paused','blocked')); END""")
        for operation, source in (("INSERT", "NEW"), ("DELETE", "OLD")):
            conn.execute(f"""CREATE TRIGGER responsibility_note_{operation.lower()}
                AFTER {operation} ON task_evidence WHEN {source}.kind='note' BEGIN UPDATE responsibility_sources
                SET dirty_generation=dirty_generation+1 WHERE source_id={source}.task_id AND responsibility_id IN
                (SELECT id FROM responsibilities WHERE status IN ('active','paused','blocked')); END""")
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute("DROP TABLE public_captures")
        conn.execute("PRAGMA user_version=1")
    return store, watch


def read_dump(store):
    with closing(sqlite3.connect(store.path)) as conn:
        return list(conn.iterdump())


def test_fresh_store_current_reopen_and_standalone_core(tmp_path):
    first = Store(tmp_path, password="fixture-only")
    assert not (tmp_path / "credentials.json").exists()
    with first.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        present = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert WATCH_TABLES.keys() <= present and "tasks" not in present
    second = Store(tmp_path, password="not-used")
    assert second.authenticate("owner", "fixture-only")


def test_legacy_default_denied_before_any_write_and_explicit_migration_preserves(tmp_path):
    old, watch = legacy_runtime(tmp_path)
    before = read_dump(old)
    with old.connection() as conn:
        old_rows = {
            name: [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")]
            for name in WATCH_TABLES
        }
        protected = {
            name: [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")]
            for name in (
                "tasks",
                "task_evidence",
                "events",
                "agent_runs",
                "private_files",
                "settings",
                "owner",
                "sessions",
                "state",
            )
        }
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        Store(tmp_path)
    assert read_dump(old) == before
    migrated = Store(tmp_path, allow_watch_retention_migration=True)
    with migrated.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute(
            "SELECT retention_state,retention_version FROM responsibilities WHERE id=?",
            (watch["id"],),
        ).fetchone()[:] == ("retained", 1)
        for name, columns in WATCH_TABLES.items():
            assert [
                tuple(row) for row in conn.execute(f"SELECT {','.join(columns)} FROM {name}")
            ] == old_rows[name]
        for name, data in protected.items():
            assert [tuple(row) for row in conn.execute(f"SELECT * FROM {name}")] == data
        triggers = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='trigger' AND name LIKE 'responsibility_%'"
        ).fetchall()
        assert len(triggers) == 5 and all(
            "retention_state='retained'" in row[0] for row in triggers
        )
    assert not (tmp_path / "credentials.json").exists()


@pytest.mark.parametrize("value", [1, "true", None, [], {}])
def test_migration_flag_requires_boolean(tmp_path, value):
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_OPT_IN_REQUIRED"):
        Store(tmp_path, allow_watch_retention_migration=value)
    assert not (tmp_path / "desk.sqlite3").exists()


def test_legacy_standalone_without_watch_tables_migrates_explicitly(tmp_path):
    store = Store(tmp_path, password="fixture-only")
    with store.connection(write=True) as conn:
        for name in (
            "responsibility_operations",
            "responsibility_reviews",
            "responsibility_sources",
            "responsibilities",
        ):
            conn.execute(f"DROP TABLE {name}")
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute("DROP TABLE public_captures")
        conn.execute("PRAGMA user_version=1")
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        Store(tmp_path)
    reopened = Store(tmp_path, allow_watch_retention_migration=True)
    with reopened.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM responsibilities").fetchone()[0] == 0


@pytest.mark.parametrize("version", [0, 4, 999])
def test_unsupported_schema_is_not_reset_or_bootstrapped(tmp_path, version):
    store = Store(tmp_path, password="fixture-only")
    with store.connection(write=True) as conn:
        conn.execute(f"PRAGMA user_version={version}")
    before = read_dump(store)
    with pytest.raises(DomainError, match="SCHEMA_VERSION_UNSUPPORTED"):
        Store(tmp_path, allow_watch_retention_migration=True)
    assert read_dump(store) == before
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == version


@pytest.mark.parametrize("kind", ["partial", "missing_index", "missing_owner", "wrong_trigger"])
def test_inconsistent_current_schema_refused_before_writes(tmp_path, kind):
    store, _ = legacy_runtime(tmp_path)
    store = Store(tmp_path, allow_watch_retention_migration=True)
    with store.connection(write=True) as conn:
        if kind == "partial":
            conn.execute("DROP TABLE responsibility_reviews")
        elif kind == "missing_index":
            conn.execute("DROP INDEX responsibilities_charged")
        elif kind == "missing_owner":
            conn.execute("DELETE FROM owner")
        else:
            conn.execute("DROP TRIGGER responsibility_task_update")
            conn.execute(
                "CREATE TRIGGER responsibility_task_update AFTER UPDATE ON tasks BEGIN SELECT 1; END"
            )
    before = read_dump(store)
    with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
        Store(tmp_path, allow_watch_retention_migration=True)
    assert read_dump(store) == before
    assert not (tmp_path / "credentials.json").exists()


@pytest.mark.parametrize(
    "marker",
    [
        "ALTER TABLE responsibilities ADD COLUMN retention_state",
        "ALTER TABLE responsibilities ADD COLUMN retention_version",
        "ALTER TABLE responsibilities ADD COLUMN trashed_at",
        "ALTER TABLE responsibilities ADD COLUMN restored_at",
        "ALTER TABLE responsibilities ADD COLUMN purged_at",
        "CREATE INDEX IF NOT EXISTS responsibilities_charged",
        "DROP TRIGGER IF EXISTS responsibility_task_update",
        "CREATE TRIGGER IF NOT EXISTS responsibility_task_update",
        "DROP TRIGGER IF EXISTS responsibility_note_delete",
        "CREATE TRIGGER IF NOT EXISTS responsibility_note_delete",
        "PRAGMA user_version=2",
    ],
)
def test_each_migration_stage_rolls_back_schema_rows_triggers_version(
    tmp_path, monkeypatch, marker
):
    store, _ = legacy_runtime(tmp_path)
    before = read_dump(store)
    original = Store.connection

    class Fault:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, statement, *args):
            result = self.conn.execute(statement, *args)
            if statement.startswith(marker):
                raise RuntimeError("Synthetic migration failure")
            return result

        def __getattr__(self, name):
            return getattr(self.conn, name)

    @contextmanager
    def connection(self, write=False):
        with original(self, write=write) as conn:
            yield Fault(conn) if write else conn

    monkeypatch.setattr(Store, "connection", connection)
    with pytest.raises(RuntimeError, match="Synthetic migration failure"):
        Store(tmp_path, allow_watch_retention_migration=True)
    monkeypatch.setattr(Store, "connection", original)
    assert read_dump(store) == before
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    Store(tmp_path, allow_watch_retention_migration=True)


def test_corrupt_legacy_watch_body_is_preserved_not_repaired(tmp_path):
    old, watch = legacy_runtime(tmp_path)
    with old.connection(write=True) as conn:
        conn.execute(
            "UPDATE responsibilities SET data='corrupt fixture body' WHERE id=?", (watch["id"],)
        )
    migrated = Store(tmp_path, allow_watch_retention_migration=True)
    with migrated.connection() as conn:
        row = conn.execute(
            "SELECT data,retention_state FROM responsibilities WHERE id=?", (watch["id"],)
        ).fetchone()
        assert row[:] == ("corrupt fixture body", "retained")


def test_coherent_sqlite_backup_readback_and_isolated_rollback_fixture(tmp_path):
    live_dir = tmp_path / "fixture-live"
    old, _ = legacy_runtime(live_dir)
    backup = tmp_path / "fixture-pre-migration.sqlite3"
    with closing(sqlite3.connect(old.path)) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
    with closing(sqlite3.connect(backup)) as check:
        assert check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert check.execute("PRAGMA user_version").fetchone()[0] == 1
        retained = check.execute("SELECT COUNT(*) FROM responsibilities").fetchone()[0]
    current = Store(live_dir, allow_watch_retention_migration=True)
    with current.connection(write=True) as conn:
        conn.execute("UPDATE state SET revision=revision+1")
    isolated = tmp_path / "fixture-isolated-rollback.sqlite3"
    with closing(sqlite3.connect(backup)) as source, closing(sqlite3.connect(isolated)) as target:
        source.backup(target)
    with closing(sqlite3.connect(isolated)) as restored:
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert restored.execute("SELECT COUNT(*) FROM responsibilities").fetchone()[0] == retained
        assert restored.execute("PRAGMA user_version").fetchone()[0] == 1
    with current.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
