"""Scheduled copies of the local SQLite file. Credentials files are not copied."""

import os
import re
import stat
from datetime import UTC, datetime, timedelta

from .calendar import iso
from .log import log_event

# Newest files kept. Older names that match the backup pattern are removed.
RETENTION = 7
# The scheduler may call tick more often; a new file is written only after this age.
MIN_AGE = timedelta(hours=24)
CHECK_INTERVAL_SECONDS = 3600
_NAME = re.compile(r"^desk-\d{8}T\d{6}Z\.sqlite3$")


def _stamp(name: str) -> datetime:
    return datetime.strptime(name[5:20], "%Y%m%dT%H%M%S").replace(tzinfo=UTC)


class LocalBackups:
    def __init__(self, runtime):
        self.store = runtime.store
        self.directory = self.store.directory / "backups"
        self.health = "idle"

    def tick(self):
        try:
            result = self._tick()
        except Exception as error:
            self.health = "retrying_after_error"
            log_event("backup", outcome="retrying_after_error", error_type=type(error).__name__)
            raise
        self.health = "ready"
        return result

    def describe(self):
        files = self._files()
        if not files:
            return {"last_at": None, "file_name": None, "bytes": None, "retained": 0}
        newest = files[-1]
        return {
            "last_at": iso(_stamp(newest.name)),
            "file_name": newest.name,
            "bytes": newest.stat().st_size,
            "retained": len(files),
        }

    def _tick(self):
        files = self._files()
        now = self.store.clock().astimezone(UTC)
        if files and now - _stamp(files[-1].name) < MIN_AGE:
            retained = self._prune(files)
            return {"written": False, "retained": retained}
        self.directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.directory, 0o700)
        name = "desk-" + now.strftime("%Y%m%dT%H%M%SZ") + ".sqlite3"
        partial = self.directory / (name + ".partial")
        target = self.directory / name
        try:
            if partial.exists():
                partial.unlink()
            self.store.backup(partial)
            os.chmod(partial, 0o600)
            os.replace(partial, target)
        finally:
            if partial.exists():
                partial.unlink()
        log_event("backup", outcome="written", file_name=name)
        retained = self._prune(self._files())
        return {"written": True, "file_name": name, "retained": retained}

    def _files(self):
        if not self.directory.is_dir():
            return []
        found = []
        for path in self.directory.iterdir():
            info = path.lstat()
            if _NAME.fullmatch(path.name) and stat.S_ISREG(info.st_mode):
                found.append(path)
        return sorted(found, key=lambda path: path.name)

    def _prune(self, files):
        extra = files[:-RETENTION] if len(files) > RETENTION else []
        for old in extra:
            old.unlink()
        return len(files) - len(extra)
