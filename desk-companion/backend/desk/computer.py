"""A replaceable, bounded executor. No shell, GUI bridge or ambient file access.

The first adapter creates new UTF-8 notes in one application-owned directory.
Only generated job IDs reach the filesystem; existing files are never overwritten.
Execution and independent verification are deliberately separate operations.
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
    ]
    artifact: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}\.txt$")
    bytes: int | None = Field(default=None, ge=0, le=MAX_BYTES, strict=True)
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
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


class LocalNotesExecutor:
    identity = "local_notes_v1"
    scope = "application_notes_only"

    def __init__(self, runtime_directory):
        self.root = Path(runtime_directory) / "computer-notes"

    def _directory(self, create=False):
        # NOFOLLOW applies to the last component. The parent is the trusted runtime
        # directory supplied by the operator, never a model-provided path.
        try:
            if create:
                self.root.mkdir(mode=0o700, exist_ok=True)
            return os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise ExecutionRejected("COMPUTER_SCOPE_UNAVAILABLE", 409) from None

    @staticmethod
    def filename(job):
        artifact = job["artifact_id"]
        if not isinstance(artifact, str) or not re.fullmatch(r"[a-f0-9]{32}", artifact):
            raise ExecutionRejected("COMPUTER_TARGET_DENIED", 403)
        return artifact + ".txt"

    def execute(self, job, checkpoint):
        filename = self.filename(job)
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
            try:
                fd = os.open(
                    filename,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=directory,
                )
            except FileExistsError:
                raise ExecutionRejected("COMPUTER_TARGET_EXISTS", 409) from None
            # Failures after open are uncertain: a partial file may exist. The
            # service must reconcile, never automatically call execute again.
            with os.fdopen(fd, "wb") as output:
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
            os.fsync(directory)
        finally:
            os.close(directory)

    def verify(self, job):
        filename = self.filename(job)
        directory = self._directory()
        try:
            try:
                fd = os.open(
                    filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
                )
            except FileNotFoundError:
                return {"verified": False, "reason": "artifact_missing"}
            except OSError:
                return {"verified": False, "reason": "target_denied"}
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
                    return {"verified": False, "reason": "target_denied"}
                body = source.read(MAX_BYTES + 1)
            digest = hashlib.sha256(body).hexdigest()
            expected = hashlib.sha256(job["content"].encode("utf-8")).hexdigest()
            return {
                "verified": digest == expected,
                "reason": "read_back_matches" if digest == expected else "content_mismatch",
                "artifact": filename,
                "bytes": len(body),
                "sha256": digest,
                "executor": self.identity,
                "scope": self.scope,
            }
        finally:
            os.close(directory)
