"""Explicit schema 2→3 migration of an existing, stopped, separately backed-up store.

Schema 1 must first use the separate watch-retention migration command.

This command neither makes nor verifies a backup, stops processes, starts the app,
accepts legal terms, or authorizes removal of any capture history.
"""

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid migration arguments; see --help.\n")


def _existing_private_database(directory):
    """Reject missing/unrecognized paths without creating an app or credential file."""
    root = Path(directory).expanduser()
    sys.path.insert(0, str(ROOT / "backend"))
    from desk.store import _migration_path_identity, _verify_migration_store

    expected = _migration_path_identity(root)
    _verify_migration_store(root, expected, {2, 3})
    return root, expected


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--runtime", required=True, help="Existing private runtime directory")
    parser.add_argument(
        "--allow-public-capture-migration",
        action="store_true",
        required=True,
        help="Acknowledge all app/workers are stopped and a coherent backup was separately verified",
    )
    args = parser.parse_args(argv)
    try:
        directory, expected = _existing_private_database(args.runtime)
        sys.path.insert(0, str(ROOT / "backend"))
        from desk.store import Store, _verify_migration_store

        version = _verify_migration_store(directory, expected, {2, 3})
        if version == 2:
            store = Store(
                directory,
                allow_public_capture_migration=True,
                _expected_migration_identity=expected,
            )
            if store.schema_version != 3:
                raise ValueError("MIGRATION_VERSION_NOT_VERIFIED")
        # Full read-only final verification, not only a version lookup. The
        # current-version verification path never invokes Store/bootstrap.
        _verify_migration_store(directory, expected, {3})
    except (OSError, ValueError, sqlite3.Error):
        print(
            "Migration not verified. No app was started; inspect the supported store and backup procedure."
        )
        return 1
    except Exception:
        # Do not print paths, stored metadata, exception payloads or credentials.
        print(
            "Migration not verified. Keep the store stopped and inspect the documented compatibility requirements."
        )
        return 1
    print("Public capture schema verified. No app was started and no capture history was removed.")
    print(
        "The flag acknowledges your backup/process checks; this command did not perform or verify them."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
