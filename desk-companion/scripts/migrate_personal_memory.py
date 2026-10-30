"""Convert original PR5 memory on an offline, separately backed-up schema3 store."""

import argparse
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--stopped-and-backed-up", action="store_true", required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from desk.memory_migration import migrate_personal_memories
    from desk.store import Store, _migration_path_identity, _verify_migration_store

    try:
        expected = _migration_path_identity(args.runtime)
        _verify_migration_store(args.runtime, expected, {3})
        store = Store(args.runtime, _expected_migration_identity=expected)
        result = migrate_personal_memories(store, acknowledged=True)
        _verify_migration_store(args.runtime, expected, {3})
    except Exception:
        print(
            "Memory conversion was not verified. Keep the store stopped and inspect its protected backup."
        )
        return 1
    print(f"Canonical memory verified; {result['migrated']} facts converted. No app was started.")
    print("The flag acknowledges operator checks; this command did not create or verify a backup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
