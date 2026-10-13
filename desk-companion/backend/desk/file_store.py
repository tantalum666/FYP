"""Private immutable byte objects with durable reservations and read-only recovery."""

import hashlib
import json
import os
import re
import stat
from uuid import uuid4

from .calendar import iso
from .store import DomainError, encode

FORMATS = {
    "text": ("txt", "text/plain; charset=utf-8"),
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "csv": ("csv", "text/csv; charset=utf-8"),
    "json": ("json", "application/json; charset=utf-8"),
}
ID = re.compile(r"^[a-f0-9]{32}$")


def digest(body):
    return hashlib.sha256(body).hexdigest()


def require_access(store, conn, session_hash):
    if not isinstance(session_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", session_hash):
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    if not conn.execute(
        "SELECT 1 FROM sessions WHERE token_hash=? AND expires>?",
        (session_hash, iso(store.clock())),
    ).fetchone():
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    if store.settings(conn)["hide_private"]:
        raise DomainError("PRIVATE_CONTEXT_HIDDEN", 403)


def session_from_request(request):
    token = request.cookies.get("desk_companion_session")
    if not token:
        raise DomainError("OWNER_SIGN_IN_REQUIRED", 403)
    return digest(token.encode())


class ImmutableFiles:
    """A file is public to this owner API only after exact independent readback.

    SQLite and filesystem are not one transaction. An existing reservation is
    never rewritten, even when a crash happened before its file was created.
    """

    def __init__(self, store):
        self.store = store
        with store.connection(write=True) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS private_files(
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, operation_key TEXT NOT NULL,
                request_hash TEXT NOT NULL, metadata TEXT NOT NULL, status TEXT NOT NULL,
                error_code TEXT, UNIQUE(kind,operation_key))""")

    def phase(self, name, row):
        """Fault-injection seam; production has no callbacks or code execution."""

    def _directory(self, kind, create=False):
        if kind not in {"sources", "artifacts"}:
            raise DomainError("FILE_TARGET_DENIED", 403)
        parent = child = None
        try:
            parent = os.open(self.store.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            if create:
                try:
                    os.mkdir(kind, mode=0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    pass
            child = os.open(kind, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            info = os.fstat(child)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise OSError("unsafe directory")
            return child
        except OSError:
            if child is not None:
                os.close(child)
            raise DomainError("FILE_SCOPE_UNAVAILABLE", 409) from None
        finally:
            if parent is not None:
                os.close(parent)

    @staticmethod
    def filename(row):
        if not ID.fullmatch(row["id"]):
            raise DomainError("FILE_TARGET_DENIED", 403)
        return row["id"] + "." + FORMATS[row["format"]][0]

    def _row(self, conn, file_id, kind):
        if not isinstance(file_id, str) or not ID.fullmatch(file_id):
            raise DomainError("FILE_NOT_FOUND", 404)
        row = conn.execute(
            "SELECT * FROM private_files WHERE id=? AND kind=?", (file_id, kind)
        ).fetchone()
        if not row:
            raise DomainError("FILE_NOT_FOUND", 404)
        return {
            **json.loads(row["metadata"]),
            "status": row["status"],
            "error_code": row["error_code"],
        }

    def metadata(self, file_id, kind, session_hash):
        with self.store.connection() as conn:
            require_access(self.store, conn, session_hash)
            return self._row(conn, file_id, kind)

    def _read_bytes(self, row):
        directory = self._directory(row["kind"])
        try:
            try:
                fd = os.open(
                    self.filename(row),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=directory,
                )
            except OSError:
                raise DomainError("FILE_READBACK_UNAVAILABLE", 409) from None
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.getuid()
                    or info.st_mode & 0o077
                    or info.st_size != row["byte_count"]
                ):
                    raise DomainError("FILE_READBACK_MISMATCH", 409)
                body = source.read(row["byte_count"] + 1)
                after = os.fstat(source.fileno())
                if (
                    after.st_nlink != 1
                    or after.st_size != len(body)
                    or len(body) != row["byte_count"]
                    or digest(body) != row["sha256"]
                ):
                    raise DomainError("FILE_READBACK_MISMATCH", 409)
                # Replaced path must not make an old open inode appear current.
                current = os.stat(self.filename(row), dir_fd=directory, follow_symlinks=False)
                if (current.st_dev, current.st_ino, current.st_nlink) != (
                    after.st_dev,
                    after.st_ino,
                    1,
                ):
                    raise DomainError("FILE_READBACK_MISMATCH", 409)
                if row["status"] != "verified":
                    # Recovery can adopt existing matching final bytes, but only
                    # after establishing the durability barrier itself. It never
                    # rewrites or republishes an unfinished temporary object.
                    os.fsync(source.fileno())
                    os.fsync(directory)
                return body
        except OSError:
            raise DomainError("FILE_READBACK_UNAVAILABLE", 409) from None
        finally:
            os.close(directory)

    def _status(self, row, state, error, session_hash):
        with self.store.connection(write=True) as conn:
            require_access(self.store, conn, session_hash)
            conn.execute(
                "UPDATE private_files SET status=?,error_code=? WHERE id=?",
                (state, error, row["id"]),
            )
        return {**row, "status": state, "error_code": error}

    def checked(self, file_id, kind, session_hash):
        row = self.metadata(file_id, kind, session_hash)
        try:
            body = self._read_bytes(row)
        except DomainError as error:
            self._status(row, "unknown", error.code, session_hash)
            raise
        row = self._status(row, "verified", None, session_hash)
        return row, body

    def reconcile(self, file_id, kind, session_hash):
        try:
            row, _ = self.checked(file_id, kind, session_hash)
            return row
        except DomainError as error:
            if error.code not in {
                "FILE_READBACK_UNAVAILABLE",
                "FILE_READBACK_MISMATCH",
                "FILE_SCOPE_UNAVAILABLE",
            }:
                raise
            return self.metadata(file_id, kind, session_hash)

    def put(self, *, kind, body, metadata, key, session_hash, max_bytes, max_count, max_total,
            checkpoint=None):
        if not key or len(key) > 100:
            raise DomainError("OPERATION_ID_REQUIRED", 422)
        if not body or len(body) > max_bytes:
            raise DomainError("FILE_SIZE_LIMIT", 413)
        expected = {**metadata, "kind": kind, "sha256": digest(body), "byte_count": len(body)}
        request_hash = digest(encode(expected).encode())
        with self.store.connection(write=True) as conn:
            require_access(self.store, conn, session_hash)
            if checkpoint is not None:
                checkpoint(conn)
            old = conn.execute(
                "SELECT * FROM private_files WHERE kind=? AND operation_key=?", (kind, key)
            ).fetchone()
            if old:
                if old["request_hash"] != request_hash:
                    raise DomainError("OPERATION_ID_CONFLICT", 409)
                file_id, fresh = old["id"], False
            else:
                rows = [
                    json.loads(r[0])
                    for r in conn.execute(
                        "SELECT metadata FROM private_files WHERE kind=?", (kind,)
                    )
                ]
                if (
                    len(rows) >= max_count
                    or sum(r["byte_count"] for r in rows) + len(body) > max_total
                ):
                    raise DomainError("FILE_CAPACITY_LIMIT", 422)
                if kind == "artifacts" and expected.get("run_id"):
                    same_run = [r for r in rows if r.get("run_id") == expected["run_id"]]
                    if (
                        len(same_run) >= 4
                        or sum(r["byte_count"] for r in same_run) + len(body) > 1024 * 1024
                    ):
                        raise DomainError("ARTIFACT_RUN_LIMIT", 422)
                file_id, fresh = uuid4().hex, True
                expected |= {"id": file_id, "created_at": iso(self.store.clock()), "version": 1}
                conn.execute(
                    "INSERT INTO private_files VALUES(?,?,?,?,?,'reserved',NULL)",
                    (file_id, kind, key, request_hash, encode(expected)),
                )
                self.store.bump(conn)
        if not fresh:
            return self.reconcile(file_id, kind, session_hash)
        row = self.metadata(file_id, kind, session_hash)
        self.phase("reserved", row)
        directory = None
        pending_created = linked = False
        try:
            directory = self._directory(kind, create=True)
            with self.store.connection() as conn:
                require_access(self.store, conn, session_hash)
                if checkpoint is not None:
                    checkpoint(conn)
            fd = os.open(
                "." + row["id"] + ".pending",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            pending_created = True
            with os.fdopen(fd, "wb") as output:
                self.phase("opened", row)
                output.write(body)
                output.flush()
                self.phase("written", row)
                os.fsync(output.fileno())
                written = os.fstat(output.fileno())
            self.phase("temp_synced", row)
            temporary = "." + row["id"] + ".pending"
            current = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_nlink) != (
                written.st_dev,
                written.st_ino,
                1,
            ):
                raise OSError("temporary identity changed")
            # Serialize the final publication point with run cancellation,
            # privacy revocation and selected-context changes. No network,
            # file writes or fsyncs happen while holding this transaction.
            with self.store.connection(write=True) as conn:
                require_access(self.store, conn, session_hash)
                if checkpoint is not None:
                    checkpoint(conn)
                os.link(
                    temporary,
                    self.filename(row),
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
                linked = True
            current = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
            final = os.stat(self.filename(row), dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino, final.st_dev, final.st_ino, current.st_nlink) != (
                written.st_dev,
                written.st_ino,
                written.st_dev,
                written.st_ino,
                2,
            ):
                raise OSError("publication identity changed")
            os.unlink(temporary, dir_fd=directory)
            self.phase("linked", row)
            os.fsync(directory)
            self.phase("synced", row)
        except DomainError:
            # Discard only this invocation's unpublished temporary body after
            # an authorization/control fence rejects it. Never erase a final
            # artifact, someone else's pending file, or unknown crash evidence.
            if directory is not None and pending_created and not linked:
                try:
                    os.unlink("." + row["id"] + ".pending", dir_fd=directory)
                    os.fsync(directory)
                except OSError:
                    pass  # Do not claim forensic erasure or mask the denial.
            raise
        except OSError:
            return self._status(row, "unknown", "FILE_WRITE_UNCERTAIN", session_hash)
        finally:
            if directory is not None:
                os.close(directory)
        result = self.reconcile(file_id, kind, session_hash)
        self.phase("published", result)
        return result

    def listing(self, kind, session_hash, *, limit=50, cursor=None, run_id=None):
        if not 1 <= limit <= 100 or (cursor is not None and not ID.fullmatch(cursor)):
            raise DomainError("VALIDATION_FAILED", 422)
        with self.store.connection() as conn:
            require_access(self.store, conn, session_hash)
            rows = [
                self._row(conn, r[0], kind)
                for r in conn.execute(
                    "SELECT id FROM private_files WHERE kind=? AND id>? ORDER BY id",
                    (kind, cursor or ""),
                )
            ]
            if run_id is not None:
                rows = [r for r in rows if r.get("run_id") == run_id]
            page = rows[:limit]
            return page, page[-1]["id"] if len(rows) > limit else None
