"""Explicit one-time migration of an existing, stopped, separately backed-up store.

This command neither makes nor verifies a backup, stops processes, starts the app,
accepts legal terms, or authorizes removal of any watch history.
"""

import argparse
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid migration arguments; see --help.\n")


def _existing_private_database(directory):
    """Reject missing/unrecognized paths without creating an app or credential file."""
    root = Path(directory).expanduser()
    root_stat = root.lstat()
    database = root / "desk.sqlite3"
    info = database.lstat()
    if (
        not stat.S_ISDIR(root_stat.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or root_stat.st_uid != os.getuid()
        or info.st_uid != os.getuid()
        or stat.S_IMODE(root_stat.st_mode) & 0o077
        or stat.S_IMODE(info.st_mode) & 0o077
        or info.st_nlink != 1
    ):
        raise ValueError("MIGRATION_PRIVATE_EXISTING_STORE_REQUIRED")
    # mode=ro avoids accidentally creating a database at an incorrect path.
    # Normal SQLite WAL handling may use its existing sidecars; immutable=1
    # would incorrectly ignore uncheckpointed WAL and is deliberately not used.
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA user_version").fetchone()[0] not in {1, 2}:
            raise ValueError("MIGRATION_SUPPORTED_STORE_REQUIRED")
        if (
            conn.execute(
                "SELECT COUNT(*) FROM owner WHERE id=1 AND typeof(password_hash)='text' "
                "AND length(password_hash)>0"
            ).fetchone()[0] != 1
            or conn.execute("SELECT COUNT(*) FROM settings WHERE id=1").fetchone()[0] != 1
            or conn.execute("SELECT COUNT(*) FROM state WHERE id=1").fetchone()[0] != 1
        ):
            raise ValueError("MIGRATION_RECOGNIZED_STORE_REQUIRED")
    after = database.lstat()
    if (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink) != (
        after.st_dev, after.st_ino, after.st_mode, after.st_uid, after.st_nlink
    ):
        raise ValueError("MIGRATION_STORE_CHANGED")
    return root


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--runtime", required=True, help="Existing private runtime directory")
    parser.add_argument(
        "--allow-watch-retention-migration", action="store_true", required=True,
        help="Acknowledge all app/workers are stopped and a coherent backup was separately verified",
    )
    args = parser.parse_args(argv)
    try:
        directory = _existing_private_database(args.runtime)
        sys.path.insert(0, str(ROOT / "backend"))
        from desk.store import Store

        store = Store(directory, allow_watch_retention_migration=True)
        with store.connection() as conn:
            if conn.execute("PRAGMA user_version").fetchone()[0] != 2:
                raise ValueError("MIGRATION_VERSION_NOT_VERIFIED")
    except (OSError, ValueError, sqlite3.Error):
        print("Migration not verified. No app was started; inspect the supported store and backup procedure.")
        return 1
    except Exception:
        # Do not print paths, stored metadata, exception payloads or credentials.
        print("Migration not verified. Keep the store stopped and inspect the documented compatibility requirements.")
        return 1
    print("Watch retention schema verified. No app was started and no watch history was removed.")
    print("The flag acknowledges your backup/process checks; this command did not perform or verify them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
