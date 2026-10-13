"""One-time operator entry: all stores and credentials here are synthetic fixtures."""

import importlib.util
from pathlib import Path
import sqlite3

import pytest

from desk.store import Store

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/migrate_watch_retention.py"
spec = importlib.util.spec_from_file_location("watch_migration_cli", SCRIPT)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def args(path):
    return ["--runtime", str(path), "--allow-watch-retention-migration"]


def fixture_store(tmp_path):
    root = tmp_path / "runtime"
    store = Store(root, password="fixture-only")
    with store.connection(write=True) as conn:
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute("DROP TABLE public_captures")
        conn.execute("PRAGMA user_version=2")
    return root, store


def test_missing_path_is_never_created(tmp_path, capsys):
    path = tmp_path / "private-marker-not-to-log"
    assert cli.main(args(path)) == 1
    assert not path.exists()
    out = capsys.readouterr()
    assert str(path) not in out.out + out.err


def test_explicit_acknowledgment_required(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--runtime", str(tmp_path / "missing")])
    assert exc.value.code == 2
    assert list(tmp_path.iterdir()) == []
    assert "missing" not in capsys.readouterr().err


def test_current_store_is_verified_without_credentials_or_history_changes(tmp_path, capsys):
    root, store = fixture_store(tmp_path)
    with store.connection() as conn:
        before = list(conn.iterdump())
    assert cli.main(args(root)) == 0
    with store.connection() as conn:
        assert list(conn.iterdump()) == before
    assert not (root / "credentials.json").exists()
    assert "did not perform or verify" in capsys.readouterr().out


def test_legacy_store_requires_explicit_entry_and_preserves_core(tmp_path):
    root, store = fixture_store(tmp_path)
    with store.connection(write=True) as conn:
        for table in ("responsibility_operations", "responsibility_reviews", "responsibility_sources", "responsibilities"):
            conn.execute(f"DROP TABLE {table}")
        conn.execute("PRAGMA user_version=1")
        conn.execute("INSERT INTO records(at,action,event_id,details) VALUES('2026-01-01','synthetic',NULL,'{}')")
    with store.connection() as conn:
        owner = conn.execute("SELECT password_hash FROM owner").fetchone()[0]
        records = [tuple(row) for row in conn.execute("SELECT * FROM records")]
    assert cli.main(args(root)) == 0
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conn.execute("SELECT password_hash FROM owner").fetchone()[0] == owner
        assert [tuple(row) for row in conn.execute("SELECT * FROM records")] == records
        assert conn.execute("SELECT count(*) FROM responsibilities").fetchone()[0] == 0
    assert not (root / "credentials.json").exists()


@pytest.mark.parametrize("unsafe", ["runtime_symlink", "database_symlink", "database_public", "runtime_public", "database_hardlink"])
def test_unsafe_path_is_refused_before_store(tmp_path, monkeypatch, unsafe):
    root, _ = fixture_store(tmp_path)
    db = root / "desk.sqlite3"
    target = root
    if unsafe == "runtime_symlink":
        target = tmp_path / "linked"
        target.symlink_to(root, target_is_directory=True)
    elif unsafe == "database_symlink":
        actual = root / "moved.sqlite3"
        db.rename(actual)
        db.symlink_to(actual)
    elif unsafe == "database_public":
        db.chmod(0o644)
    elif unsafe == "runtime_public":
        root.chmod(0o755)
    else:
        (root / "extra.sqlite3").hardlink_to(db)
    monkeypatch.setattr("desk.store.Store", lambda *a, **k: pytest.fail("Store must not run"))
    assert cli.main(args(target)) == 1
    assert not (root / "credentials.json").exists()


@pytest.mark.parametrize("invalid", ["forward_version", "missing_owner", "unrecognized"])
def test_unrecognized_database_never_bootstraps(tmp_path, monkeypatch, invalid):
    root, store = fixture_store(tmp_path)
    with store.connection(write=True) as conn:
        if invalid == "forward_version":
            conn.execute("PRAGMA user_version=999")
        elif invalid == "missing_owner":
            conn.execute("DELETE FROM owner")
        else:
            conn.execute("DROP TABLE settings")
    monkeypatch.setattr("desk.store.Store", lambda *a, **k: pytest.fail("Store must not run"))
    assert cli.main(args(root)) == 1
    assert not (root / "credentials.json").exists()


def test_store_failure_does_not_echo_path_or_error_payload(tmp_path, monkeypatch, capsys):
    root, store = fixture_store(tmp_path)
    with store.connection(write=True) as conn:
        for table in ("responsibility_operations", "responsibility_reviews", "responsibility_sources", "responsibilities"):
            conn.execute(f"DROP TABLE {table}")
        conn.execute("PRAGMA user_version=1")

    def fail(*args, **kwargs):
        raise RuntimeError("MUST_NOT_ECHO_SYNTHETIC")

    monkeypatch.setattr("desk.store.Store", fail)
    assert cli.main(args(root)) == 1
    assert "MUST_NOT_ECHO_SYNTHETIC" not in capsys.readouterr().out


def test_read_handle_is_closed_before_store(tmp_path, monkeypatch):
    root, _ = fixture_store(tmp_path)
    original = sqlite3.connect
    reads = []

    def connect(*args, **kwargs):
        result = original(*args, **kwargs)
        reads.append(result)
        return result

    monkeypatch.setattr(cli.sqlite3, "connect", connect)
    cli._existing_private_database(root)
    assert len(reads) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        reads[0].execute("SELECT 1")


def test_app_factory_does_not_infer_legacy_migration_consent(tmp_path):
    from desk.app import create_app
    from desk.store import DomainError

    root, store = fixture_store(tmp_path)
    with store.connection(write=True) as conn:
        for table in ("responsibility_operations", "responsibility_reviews", "responsibility_sources", "responsibilities"):
            conn.execute(f"DROP TABLE {table}")
        conn.execute("PRAGMA user_version=1")
    with pytest.raises(DomainError) as error:
        create_app(directory=root, scheduler=False)
    assert error.value.code == "SCHEMA_MIGRATION_REQUIRED"
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        create_app(directory=root, scheduler=False, allow_watch_retention_migration=True)
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert not (root / "credentials.json").exists()
