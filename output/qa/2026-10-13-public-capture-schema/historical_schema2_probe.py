"""Run the exact archived schema-2 Store against synthetic schema-3 fixtures.

Usage: python historical_schema2_probe.py path/to/archived-store.py
Source must be independently pinned to the published cc1751a artifact by coordinator.
No user runtime, credentials, live network or old full application is involved.
"""

from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "desk-companion/backend"))
from desk.store import Store  # noqa: E402

source = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("desk.old_schema2_store", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = []
with tempfile.TemporaryDirectory(prefix="synthetic-capture-schema-") as directory:
    root = Path(directory)
    current = Store(root, password="synthetic-only")
    with closing(sqlite3.connect(current.path, isolation_level=None)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    before = current.path.read_bytes()
    for opt_in in (False, True):
        try:
            module.Store(root, allow_watch_retention_migration=opt_in)
        except module.DomainError as error:
            assert error.code == "SCHEMA_VERSION_UNSUPPORTED"
            results.append({"watch_migration_flag": opt_in, "code": error.code})
        else:
            raise AssertionError("Historical schema2 Store unexpectedly accepted schema3")
        assert current.path.read_bytes() == before
        assert not (root / "credentials.json").exists()
    with current.connection(write=True) as conn:
        conn.execute("DROP TABLE public_capture_operations")
        conn.execute("DROP TABLE public_captures")
        conn.execute("PRAGMA user_version=2")
    historical = module.Store(root)
    with historical.connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='public_captures'").fetchone()
print(json.dumps({
    "historical_source_revision": "cc1751a",
    "historical_store_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "schema3_refused_without_database_changes": results,
    "historical_v2_store_still_accepted": True,
    "scope": "Exact archived Store module, unchanged relative dependencies; synthetic SQLite only, not a historical full-app acceptance test",
}, indent=2))
