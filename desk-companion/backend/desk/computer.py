"""Replaceable, bounded executors. No shell, GUI bridge or ambient file access.

Both adapters create one new UTF-8 file whose name is the generated job ID.
Existing files are never overwritten. Execution and independent verification
are separate operations. The notes adapter uses the application runtime
directory. The folder adapter uses only the single real directory the owner
named; the model cannot supply a path.
"""

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import Field, model_validator

from .schemas import StrictModel

from .store import DomainError

MAX_BYTES = 32_000


class VerificationReceipt(StrictModel):
    verified: bool = Field(strict=True)
    reason: Literal[
        "read_back_matches",
        "artifact_missing",
        "target_denied",
        "content_mismatch",
        "verification_unavailable",
        "workflow_incomplete",
    ]
    artifact: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}\.txt$")
    bytes: int | None = Field(default=None, ge=0, le=MAX_BYTES, strict=True)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    apps_verified: list[Literal["mousepad", "chromium"]] | None = None
    executor: str | None = None
    scope: str | None = None

    @model_validator(mode="after")
    def complete_evidence(self):
        if self.verified and (
            self.reason != "read_back_matches"
            or any(
                value is None
                for value in (self.artifact, self.bytes, self.sha256, self.executor, self.scope)
            )
        ):
            raise ValueError("Success requires a complete independent receipt")
        return self


class ExecutionRejected(DomainError):
    """The adapter rejected this request before causing a side effect."""


class ComputerExecutor(Protocol):
    identity: str
    scope: str

    def execute(self, job: dict, checkpoint: Callable[[], None]) -> None: ...

    def verify(self, job: dict) -> dict: ...


def open_real_directory(root: Path, *, create: bool) -> int:
    """Open a directory inode. The last component is not followed if it is a link."""
    try:
        if create:
            root.mkdir(mode=0o700, exist_ok=True)
        return os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise ExecutionRejected("COMPUTER_SCOPE_UNAVAILABLE", 409) from None


def artifact_filename(job) -> str:
    """The only permitted name is the generated job id plus .txt."""
    artifact = job["artifact_id"]
    if not isinstance(artifact, str) or not re.fullmatch(r"[a-f0-9]{32}", artifact):
        raise ExecutionRejected("COMPUTER_TARGET_DENIED", 403)
    return artifact + ".txt"


def exclusive_write(directory: int, filename: str, body: bytes) -> None:
    """Create a new regular file. An existing name is left untouched."""
    try:
        fd = os.open(
            filename,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
    except FileExistsError:
        raise ExecutionRejected("COMPUTER_TARGET_EXISTS", 409) from None
    # Failures after open are uncertain: a partial file may exist.
    with os.fdopen(fd, "wb") as output:
        output.write(body)
        output.flush()
        os.fsync(output.fileno())
    os.fsync(directory)


def open_owner_directory(root: Path) -> int:
    """Walk the approved absolute path without following links in any component.

    Directory handles pin each parent while opening the next component, closing
    the race between path validation and an ancestor being replaced by a link.
    """
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = None
    try:
        directory = os.open(root.anchor, flags)
        for component in root.parts[1:]:
            child = os.open(component, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        result, directory = directory, None
        return result
    except OSError:
        raise ExecutionRejected("COMPUTER_SCOPE_UNAVAILABLE", 409) from None
    finally:
        if directory is not None:
            os.close(directory)


def read_artifact(
    directory: int, filename: str, expected: bytes, identity: str, scope: str
) -> dict:
    """Read the file back through a separate open. This does not repair it."""
    try:
        fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return {"verified": False, "reason": "artifact_missing"}
    except OSError:
        return {"verified": False, "reason": "target_denied"}
    # A directory can be opened on Linux, and fdopen then raises. Reject it
    # before that so verification stays an unverified receipt.
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
        os.close(fd)
        return {"verified": False, "reason": "target_denied"}
    with os.fdopen(fd, "rb") as source:
        body = source.read(MAX_BYTES + 1)
    digest = hashlib.sha256(body).hexdigest()
    matched = digest == hashlib.sha256(expected).hexdigest()
    return {
        "verified": matched,
        "reason": "read_back_matches" if matched else "content_mismatch",
        "artifact": filename,
        "bytes": len(body),
        "sha256": digest,
        "executor": identity,
        "scope": scope,
    }


def accept_owner_folder(raw: str, runtime_directory: Path) -> tuple[str, str]:
    """Accept one absolute real directory outside the desk runtime tree.

    The model never supplies this path. Symlinks, missing paths, files, the
    runtime directory, its parents and its children are rejected.
    """
    if not isinstance(raw, str) or "\x00" in raw or len(raw) > 4096:
        raise DomainError("FOLDER_PATH_DENIED", 422)
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise DomainError("FOLDER_PATH_DENIED", 422)
    try:
        lexical = Path(os.path.abspath(candidate))
        resolved = lexical.resolve(strict=True)
        info = os.lstat(resolved)
    except OSError:
        raise DomainError("FOLDER_PATH_DENIED", 422) from None
    if resolved != lexical or stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise DomainError("FOLDER_PATH_DENIED", 422)
    runtime = Path(runtime_directory).resolve()
    if resolved == runtime or runtime in resolved.parents or resolved in runtime.parents:
        raise DomainError("FOLDER_PATH_DENIED", 422)
    return str(resolved), hashlib.sha256(str(resolved).encode()).hexdigest()


class LocalNotesExecutor:
    identity = "local_notes_v1"
    scope = "application_notes_only"

    def __init__(self, runtime_directory):
        self.root = Path(runtime_directory) / "computer-notes"

    def _directory(self, create=False):
        # The parent is the trusted runtime directory supplied by the operator,
        # never a model-provided path.
        return open_real_directory(self.root, create=create)

    def execute(self, job, checkpoint):
        filename = artifact_filename(job)
        if job["action"] not in {"save_note", "verify_note"}:
            raise ExecutionRejected("COMPUTER_ACTION_DENIED", 403)
        body = job["content"].encode("utf-8")
        if len(body) > MAX_BYTES:
            raise ExecutionRejected("COMPUTER_CONTENT_TOO_LARGE", 422)
        directory = self._directory(create=True)
        try:
            checkpoint()  # Immediately before the first possible external effect.
            if job["action"] == "verify_note":
                return
            exclusive_write(directory, filename, body)
        finally:
            os.close(directory)

    def verify(self, job):
        filename = artifact_filename(job)
        directory = self._directory()
        try:
            return read_artifact(
                directory,
                filename,
                job["content"].encode("utf-8"),
                self.identity,
                self.scope,
            )
        finally:
            os.close(directory)


class FolderDropExecutor:
    """Write one new text file into the single directory the owner named.

    The path lives in SQLite and is re-checked on every use. Job payloads carry
    the label and a fingerprint, never the path itself.
    """

    identity = "folder_drop_v1"

    def __init__(self, lookup: Callable[[], dict | None]):
        self.lookup = lookup

    def configuration(self):
        return self.lookup()

    @property
    def configured(self):
        return self.configuration() is not None

    @property
    def scope(self):
        cfg = self.configuration()
        if not cfg:
            return "owner_folder_unconfigured"
        return "owner_folder:" + cfg["fingerprint"]

    def _bound_root(self, job):
        cfg = self.configuration()
        if (
            not cfg
            or job.get("folder_fingerprint") != cfg["fingerprint"]
            or job.get("scope") != self.scope
            or job.get("executor") != self.identity
        ):
            raise ExecutionRejected("COMPUTER_SCOPE_CHANGED", 409)
        if job["action"] not in {"save_folder_file", "verify_folder_file"}:
            raise ExecutionRejected("COMPUTER_ACTION_DENIED", 403)
        root = Path(cfg["path"])
        try:
            lexical = Path(os.path.abspath(root))
            resolved = lexical.resolve(strict=True)
        except OSError:
            raise ExecutionRejected("COMPUTER_SCOPE_UNAVAILABLE", 409) from None
        if str(resolved) != cfg["path"] or resolved != lexical:
            raise ExecutionRejected("COMPUTER_SCOPE_CHANGED", 409)
        return root

    def execute(self, job, checkpoint):
        filename = artifact_filename(job)
        root = self._bound_root(job)
        body = job["content"].encode("utf-8")
        if len(body) > MAX_BYTES:
            raise ExecutionRejected("COMPUTER_CONTENT_TOO_LARGE", 422)
        directory = open_owner_directory(root)
        try:
            checkpoint()
            if job["action"] == "verify_folder_file":
                return
            exclusive_write(directory, filename, body)
        finally:
            os.close(directory)

    def verify(self, job):
        filename = artifact_filename(job)
        root = self._bound_root(job)
        directory = open_owner_directory(root)
        try:
            return read_artifact(
                directory, filename, job["content"].encode("utf-8"), self.identity, self.scope
            )
        finally:
            os.close(directory)
