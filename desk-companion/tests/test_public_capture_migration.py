"""Schema lifecycle on isolated synthetic stores; no user runtime is migrated."""

from contextlib import closing, contextmanager
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from desk.public_capture_schema import (
    CAPTURE_DDL,
    CAPTURE_INDEX_DDL,
    validate_public_capture_schema,
)
from desk.store import DomainError, Store
from test_watch_retention_migration import legacy_runtime, read_dump

ROOT = Path(__file__).resolve().parents[1]


def version2(tmp_path):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute("DROP TABLE public_captures")
        conn.execute("PRAGMA user_version=2")
    return store


def capture_row(conn, **changes):
    row = {
        "id": "a" * 32,
        "state": "review",
        "version": 1,
        "intent_json": "{}",
        "intent_hash": "b" * 64,
        "policy_version": 1,
        "session_hash": "c" * 64,
        "privacy_revision": "1:1",
        "generation": 0,
        "created_at": "2026-10-13T00:00:00Z",
        "updated_at": "2026-10-13T00:00:00Z",
        "expires_at": "2026-10-13T00:05:00Z",
        "source_operation_key": "public-capture:" + "a" * 32,
        "stage": "review",
    }
    row.update(changes)
    conn.execute(
        f"INSERT INTO public_captures({','.join(row)}) VALUES({','.join('?' for _ in row)})",
        list(row.values()),
    )


def test_fresh_current_store_validates_and_reopens_without_credentials(tmp_path):
    first = Store(tmp_path, password="synthetic-only")
    assert first.schema_version == 3
    with first.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        validate_public_capture_schema(conn)
    second = Store(tmp_path)
    assert second.schema_version == 3
    assert not (tmp_path / "credentials.json").exists()


@pytest.mark.parametrize("watch", [False, True])
def test_v2_default_denied_before_journal_or_bootstrap(tmp_path, monkeypatch, watch):
    old = version2(tmp_path)
    with closing(sqlite3.connect(old.path, isolation_level=None)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    before = old.path.read_bytes()
    original = sqlite3.connect
    calls = []

    def connect(*args, **kwargs):
        calls.append((args, kwargs))
        assert kwargs.get("uri") and args[0].endswith("?mode=ro")
        return original(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        Store(tmp_path, allow_watch_retention_migration=watch)
    assert len(calls) == 1
    assert old.path.read_bytes() == before
    assert not (tmp_path / "credentials.json").exists()


def test_v2_explicit_preserves_all_prior_rows_and_atomic_version(tmp_path):
    old = version2(tmp_path)
    before = read_dump(old)
    current = Store(tmp_path, allow_public_capture_migration=True)
    assert current.schema_version == 3
    with current.connection() as conn:
        validate_public_capture_schema(conn)
        after = list(conn.iterdump())
    assert set(before) <= set(after)
    assert Store(tmp_path).schema_version == 3
    assert not (tmp_path / "credentials.json").exists()


@pytest.mark.parametrize("value", [1, 0, "true", None, [], {}])
def test_capture_flag_strict_bool_before_creation(tmp_path, value):
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_OPT_IN_REQUIRED"):
        Store(tmp_path, allow_public_capture_migration=value)
    assert not (tmp_path / "desk.sqlite3").exists()


@pytest.mark.parametrize("watch", [False, True])
def test_v1_cannot_skip_or_combine_migration(tmp_path, watch):
    old, _ = legacy_runtime(tmp_path)
    before = read_dump(old)
    with pytest.raises(DomainError, match="SCHEMA_STAGED_MIGRATION_REQUIRED"):
        Store(tmp_path, allow_watch_retention_migration=watch, allow_public_capture_migration=True)
    assert read_dump(old) == before
    intermediate = Store(tmp_path, allow_watch_retention_migration=True)
    assert intermediate.schema_version == 2
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        Store(tmp_path)
    assert Store(tmp_path, allow_public_capture_migration=True).schema_version == 3


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize("partial", [True, False])
def test_legacy_unexpected_capture_schema_never_adopted(tmp_path, version, partial):
    old = Store(tmp_path, password="synthetic-only")
    with old.connection(write=True) as conn:
        if partial:
            conn.execute("DROP TABLE public_capture_operations")
        conn.execute(f"PRAGMA user_version={version}")
    before = read_dump(old)
    with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
        Store(tmp_path, allow_public_capture_migration=True)
    assert read_dump(old) == before


@pytest.mark.parametrize(
    "damage",
    [
        "missing_both",
        "missing_one",
        "index",
        "wrong_index",
        "check",
        "fk",
        "unique",
        "trigger",
        "identity",
        "orphan",
        "base_identity",
    ],
)
def test_current_damage_rejected_without_repair_even_when_disabled(tmp_path, damage):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        if damage == "missing_both":
            conn.execute("DROP TABLE public_capture_operations")
            conn.execute("DROP TABLE public_captures")
        elif damage == "missing_one":
            conn.execute("DROP TABLE public_capture_operations")
        elif damage in {"index", "wrong_index"}:
            conn.execute("DROP INDEX public_captures_created")
            if damage == "wrong_index":
                conn.execute("CREATE INDEX public_captures_created ON public_captures(id)")
        elif damage in {"check", "fk", "unique"}:
            conn.execute("DROP TABLE public_capture_operations")
            sql = CAPTURE_DDL[1]
            if damage == "check":
                sql = sql.replace("CHECK(kind IN('prepare','approve','cancel'))", "")
            elif damage == "fk":
                sql = sql.replace("FOREIGN KEY(capture_id) REFERENCES public_captures(id),", "")
            else:
                sql = sql.replace(",\n        UNIQUE(capture_id,kind)", "")
            conn.execute(sql)
            conn.execute(CAPTURE_INDEX_DDL[1])
        elif damage == "trigger":
            conn.execute(
                "CREATE TRIGGER synthetic_bad AFTER INSERT ON public_captures BEGIN DELETE FROM public_capture_operations; END"
            )
        elif damage == "identity":
            conn.execute("PRAGMA ignore_check_constraints=ON")
            capture_row(conn, id="bad")
        elif damage == "base_identity":
            conn.execute("DELETE FROM owner")
        else:
            capture_row(conn)
    if damage == "orphan":
        with closing(sqlite3.connect(store.path)) as conn:
            conn.execute(
                "INSERT INTO public_capture_operations VALUES('orphan','prepare',?,?)",
                ("b" * 64, "d" * 32),
            )
            conn.commit()
    before = read_dump(store)
    with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
        Store(tmp_path)
    assert read_dump(store) == before


def test_private_json_corruption_not_a_structural_startup_dependency(tmp_path):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        capture_row(conn, intent_json="bad private JSON", acquisition_json="bad private JSON")
    assert Store(tmp_path).schema_version == 3


MIGRATION_MARKERS = [
    "CREATE TABLE public_captures",
    "CREATE TABLE public_capture_operations",
    *CAPTURE_INDEX_DDL,
    "PRAGMA user_version=3",
]


@pytest.mark.parametrize("marker", MIGRATION_MARKERS)
def test_every_capture_migration_stage_rolls_back(tmp_path, monkeypatch, marker):
    old = version2(tmp_path)
    before = read_dump(old)
    original = Store.connection

    class Fault:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, statement, *args):
            result = self.conn.execute(statement, *args)
            if statement.startswith(marker):
                raise RuntimeError("Synthetic rollback")
            return result

        def __getattr__(self, name):
            return getattr(self.conn, name)

    @contextmanager
    def connection(self, write=False):
        with original(self, write=write) as conn:
            yield Fault(conn) if write else conn

    monkeypatch.setattr(Store, "connection", connection)
    with pytest.raises(RuntimeError, match="Synthetic rollback"):
        Store(tmp_path, allow_public_capture_migration=True)
    monkeypatch.setattr(Store, "connection", original)
    assert read_dump(old) == before
    assert Store(tmp_path, allow_public_capture_migration=True).schema_version == 3


@pytest.mark.parametrize("marker", MIGRATION_MARKERS)
def test_process_exit_at_each_uncommitted_stage_remains_valid_v2(tmp_path, marker):
    old = version2(tmp_path)
    before = read_dump(old)
    program = """
import os, sys
from contextlib import contextmanager
from desk.store import Store
original = Store.connection
class Exit:
    def __init__(self, conn): self.conn = conn
    def execute(self, statement, *args):
        result = self.conn.execute(statement, *args)
        if statement.startswith(sys.argv[2]): os._exit(73)
        return result
    def __getattr__(self, name): return getattr(self.conn, name)
@contextmanager
def connection(self, write=False):
    with original(self, write=write) as conn:
        yield Exit(conn) if write else conn
Store.connection = connection
Store(sys.argv[1], allow_public_capture_migration=True)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'backend');\n" + program,
            str(tmp_path),
            marker,
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 73, result.stderr
    assert read_dump(old) == before
    with old.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
    assert Store(tmp_path, allow_public_capture_migration=True).schema_version == 3


def cli_module():
    spec = importlib.util.spec_from_file_location(
        "public_capture_cli", ROOT / "scripts/migrate_public_capture.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli


def cli_args(root):
    return ["--runtime", str(root), "--allow-public-capture-migration"]


def test_cli_v2_upgrade_and_v3_readonly_verification(tmp_path, monkeypatch, capsys):
    root = tmp_path / "runtime"
    old = version2(root)
    cli = cli_module()
    assert cli.main(cli_args(root)) == 0
    before = read_dump(old)
    monkeypatch.setattr(
        "desk.store.Store", lambda *a, **k: pytest.fail("No initialization on v3 verification")
    )
    assert cli.main(cli_args(root)) == 0
    assert read_dump(old) == before
    assert "did not perform or verify" in capsys.readouterr().out
    assert not (root / "credentials.json").exists()


def test_cli_missing_ack_and_missing_path_create_nothing(tmp_path, capsys):
    cli = cli_module()
    root = tmp_path / "private-do-not-echo"
    with pytest.raises(SystemExit) as error:
        cli.main(["--runtime", str(root)])
    assert error.value.code == 2
    assert cli.main(cli_args(root)) == 1
    assert not root.exists()
    out = capsys.readouterr()
    assert str(root) not in out.out + out.err


@pytest.mark.parametrize(
    "unsafe",
    [
        "directory_symlink",
        "database_symlink",
        "hardlink",
        "public_root",
        "public_database",
        "fifo",
        "v1",
        "forward",
        "partial",
    ],
)
def test_cli_preflight_refuses_unsafe_or_unrecognized_store(tmp_path, monkeypatch, unsafe):
    root = tmp_path / "runtime"
    old = version2(root)
    database = old.path
    target = root
    if unsafe == "directory_symlink":
        target = tmp_path / "link"
        target.symlink_to(root, target_is_directory=True)
    elif unsafe == "database_symlink":
        moved = root / "moved.sqlite3"
        database.rename(moved)
        database.symlink_to(moved)
    elif unsafe == "hardlink":
        (root / "link.sqlite3").hardlink_to(database)
    elif unsafe == "public_root":
        root.chmod(0o755)
    elif unsafe == "public_database":
        database.chmod(0o644)
    elif unsafe == "fifo":
        import os

        database.unlink()
        os.mkfifo(database)
    else:
        with old.connection(write=True) as conn:
            if unsafe in {"v1", "forward"}:
                conn.execute("PRAGMA user_version=" + ("1" if unsafe == "v1" else "999"))
            else:
                conn.execute(CAPTURE_DDL[0])
    monkeypatch.setattr(
        "desk.store.Store", lambda *a, **k: pytest.fail("Preflight must fail before Store")
    )
    assert cli_module().main(cli_args(target)) == 1
    assert not (root / "credentials.json").exists()


def test_quoted_constraint_whitespace_is_not_normalized(tmp_path):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute(CAPTURE_DDL[1].replace("'prepare'", "'pre pare'"))
        conn.execute(CAPTURE_INDEX_DDL[1])
    with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
        Store(tmp_path)


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "state",
        "version",
        "intent_hash",
        "session_hash",
        "generation",
        "source_operation_key",
        "source_id",
    ],
)
def test_corrupt_capture_scalar_is_bounded_before_python_materialization(tmp_path, field):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        conn.execute("PRAGMA ignore_check_constraints=ON")
        capture_row(conn, **{field: "x" * (1024 * 1024)})
    projected = []
    with closing(sqlite3.connect(store.path)) as conn:

        def rows(cursor, values):
            if cursor.description and cursor.description[0][0].startswith("CASE"):
                projected.extend(values)
            return values

        conn.row_factory = rows
        with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
            validate_public_capture_schema(conn)
    assert projected and all(not isinstance(value, str) or len(value) <= 100 for value in projected)


@pytest.mark.parametrize("field", ["operation_key", "kind", "request_hash", "capture_id"])
def test_corrupt_operation_scalar_is_bounded_before_python_materialization(tmp_path, field):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        capture_row(conn)
    with closing(sqlite3.connect(store.path)) as conn:
        conn.execute("PRAGMA ignore_check_constraints=ON")
        fields = {
            "operation_key": "test",
            "kind": "prepare",
            "request_hash": "b" * 64,
            "capture_id": "a" * 32,
        }
        fields[field] = "x" * (1024 * 1024)
        conn.execute("INSERT INTO public_capture_operations VALUES(?,?,?,?)", list(fields.values()))
        conn.commit()
        projected = []

        def rows(cursor, values):
            if cursor.description and cursor.description[0][0].startswith("CASE"):
                projected.extend(values)
            return values

        conn.row_factory = rows
        with pytest.raises(DomainError, match="SCHEMA_STRUCTURE_UNSUPPORTED"):
            validate_public_capture_schema(conn)
    assert projected and all(not isinstance(value, str) or len(value) <= 100 for value in projected)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "a" * 32 + "\x00x"),
        ("version", 2**53),
        ("generation", 2**53),
        ("source_id", "f" * 32 + "\x00x"),
    ],
)
def test_constraints_reject_nul_identity_and_unsafe_integer(tmp_path, field, value):
    store = Store(tmp_path, password="synthetic-only")
    with store.connection(write=True) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            capture_row(conn, **{field: value})


def test_old_watch_cli_refuses_schema3_instead_of_downgrading(tmp_path, monkeypatch):
    store = Store(tmp_path, password="synthetic-only")
    before = read_dump(store)
    spec = importlib.util.spec_from_file_location(
        "watch_migration_cli", ROOT / "scripts/migrate_watch_retention.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr(
        "desk.store.Store",
        lambda *a, **k: pytest.fail("Future-version verification cannot initialize Store"),
    )
    assert cli.main(["--runtime", str(tmp_path), "--allow-watch-retention-migration"]) == 1
    assert read_dump(store) == before


def test_process_exit_immediately_after_commit_reopens_complete_v3(tmp_path):
    old = version2(tmp_path)
    program = """
import os, sys
from contextlib import contextmanager
from desk.store import Store
original = Store.connection
@contextmanager
def connection(self, write=False):
    with original(self, write=write) as conn:
        yield conn
    if write: os._exit(74)
Store.connection = connection
Store(sys.argv[1], allow_public_capture_migration=True)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, 'backend');\n" + program,
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 74, result.stderr
    with old.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3
        validate_public_capture_schema(conn)
    assert Store(tmp_path).schema_version == 3


@pytest.mark.parametrize("change", ["version", "structure"])
def test_migration_rechecks_under_transaction_before_bootstrap(tmp_path, monkeypatch, change):
    old = version2(tmp_path)
    original = Store.connection

    @contextmanager
    def connection(self, write=False):
        if write:
            with closing(sqlite3.connect(self.path)) as outside:
                if change == "version":
                    outside.execute("PRAGMA user_version=999")
                else:
                    outside.execute("DROP TABLE owner")
                outside.commit()
        with original(self, write=write) as conn:
            yield conn

    monkeypatch.setattr(Store, "connection", connection)
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_INVALID|SCHEMA_STRUCTURE_UNSUPPORTED"):
        Store(tmp_path, allow_public_capture_migration=True)
    monkeypatch.setattr(Store, "connection", original)
    with old.connection() as conn:
        assert not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='public_captures'"
        ).fetchone()
        if change == "structure":
            assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='owner'").fetchone()
    assert not (tmp_path / "credentials.json").exists()


def test_runtime_v2_needs_distinct_explicit_capture_migration(tmp_path):
    from desk.app import create_app

    old = version2(tmp_path)
    before = read_dump(old)
    with pytest.raises(DomainError, match="SCHEMA_MIGRATION_REQUIRED"):
        create_app(directory=tmp_path, scheduler=False)
    assert read_dump(old) == before
    app = create_app(directory=tmp_path, scheduler=False, allow_public_capture_migration=True)
    assert app is not None
    assert Store(tmp_path).schema_version == 3


def operator_cli(kind):
    name = "migrate_public_capture" if kind == "capture" else "migrate_watch_retention"
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    return cli


@pytest.mark.parametrize("kind", ["capture", "watch"])
@pytest.mark.parametrize("change", ["symlink", "replacement", "public_database", "public_root"])
def test_cli_binds_preflight_identity_and_permissions_before_migration(
    tmp_path, monkeypatch, kind, change
):
    approved = tmp_path / "approved"
    other = tmp_path / "unapproved"
    if kind == "capture":
        old, alternate = version2(approved), version2(other)
    else:
        old, _ = legacy_runtime(approved)
        alternate, _ = legacy_runtime(other)
    before_other = read_dump(alternate)
    cli = operator_cli(kind)
    original = cli._existing_private_database

    def swapped(directory):
        result = original(directory)
        if change == "symlink":
            old.path.rename(approved / "saved.sqlite3")
            old.path.symlink_to(alternate.path)
        elif change == "replacement":
            old.path.rename(approved / "saved.sqlite3")
            with (
                closing(sqlite3.connect(alternate.path)) as source,
                closing(sqlite3.connect(old.path)) as target,
            ):
                source.backup(target)
            old.path.chmod(0o600)
        elif change == "public_database":
            old.path.chmod(0o644)
        else:
            approved.chmod(0o755)
        return result

    monkeypatch.setattr(cli, "_existing_private_database", swapped)
    flag = (
        "--allow-public-capture-migration"
        if kind == "capture"
        else "--allow-watch-retention-migration"
    )
    assert cli.main(["--runtime", str(approved), flag]) == 1
    assert read_dump(alternate) == before_other
    assert not (approved / "credentials.json").exists()


@pytest.mark.parametrize("kind", ["capture", "watch"])
def test_cli_current_version_rechecks_full_schema_after_preflight(tmp_path, monkeypatch, kind):
    store = Store(tmp_path, password="synthetic-only") if kind == "capture" else version2(tmp_path)
    cli = operator_cli(kind)
    original = cli._existing_private_database

    def damaged(directory):
        result = original(directory)
        with store.connection(write=True) as conn:
            conn.execute("DROP TABLE owner")
        return result

    monkeypatch.setattr(cli, "_existing_private_database", damaged)
    flag = (
        "--allow-public-capture-migration"
        if kind == "capture"
        else "--allow-watch-retention-migration"
    )
    assert cli.main(["--runtime", str(tmp_path), flag]) == 1
    with store.connection() as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='owner'").fetchone()


@pytest.mark.parametrize("stage", ["before_journal", "journal_open", "write_open"])
def test_migration_identity_rechecked_at_sqlite_open_boundaries(tmp_path, monkeypatch, stage):
    root, other = tmp_path / "approved", tmp_path / "unapproved"
    old, alternate = version2(root), version2(other)
    before = read_dump(alternate)
    expected = __import__(
        "desk.store", fromlist=["_migration_path_identity"]
    )._migration_path_identity(root)
    original = sqlite3.connect
    calls = 0

    def swap():
        old.path.rename(root / "saved.sqlite3")
        old.path.symlink_to(alternate.path)

    def connect(*args, **kwargs):
        nonlocal calls
        if str(args[0]) != ":memory:":
            calls += 1
        if calls == 1 and stage == "before_journal":
            conn = original(*args, **kwargs)
            swap()
            return conn
        if calls == 2 and stage == "journal_open":
            swap()
        if calls == 3 and stage == "write_open":
            swap()
        return original(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(
        DomainError, match="MIGRATION_PRIVATE_EXISTING_STORE_REQUIRED|MIGRATION_STORE_CHANGED"
    ):
        Store(root, allow_public_capture_migration=True, _expected_migration_identity=expected)
    monkeypatch.setattr(sqlite3, "connect", original)
    assert read_dump(alternate) == before


@pytest.mark.parametrize("kind", ["capture", "watch"])
def test_migration_preserves_preflighted_private_owner_mode(tmp_path, kind):
    if kind == "capture":
        store = version2(tmp_path)
    else:
        store, _ = legacy_runtime(tmp_path)
    store.path.chmod(0o700)
    cli = operator_cli(kind)
    flag = (
        "--allow-public-capture-migration"
        if kind == "capture"
        else "--allow-watch-retention-migration"
    )
    assert cli.main(["--runtime", str(tmp_path), flag]) == 0
    assert store.path.stat().st_mode & 0o777 == 0o700
    with store.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == (3 if kind == "capture" else 2)
