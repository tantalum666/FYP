"""Fixed, job-owned browser worker supervision. Never launches a caller's command.

Only this worker's new process group may be forcibly stopped. A forced kill or
missing browser-close acknowledgment is NOT proof that every browser child exited;
the service must block later admission pending independently confirmed cleanup.
"""

import importlib.util
import json
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .store import DomainError

STAGES = {
    "read_source",
    "open_editor",
    "dismiss_tour",
    "open_explorer",
    "new_file",
    "name_file",
    "confirm_file",
    "fill_editor",
    "open_menu",
    "open_export",
    "export",
}


@dataclass(frozen=True)
class WorkerOutcome:
    value: dict | None
    error: str | None
    dispatched: bool
    cleanup_confirmed: bool
    forced_stop: bool = False


class BrowserSupervisor:
    worker_module = "desk.browser_worker"
    stage_names = STAGES
    stage_limit = 20
    protocol_limit = 128 * 1024

    def __init__(self, executable=None):
        self.executable = executable or os.environ.get("DESK_BROWSER_EXECUTABLE", "")

    def readiness(self):
        if sys.platform not in {"linux", "darwin"}:
            return "BROWSER_PLATFORM_UNSUPPORTED"
        if importlib.util.find_spec("playwright") is None:
            return "BROWSER_EXTRA_REQUIRED"
        path = Path(self.executable)
        if not self.executable or not path.is_absolute() or not path.is_file():
            return "BROWSER_EXECUTABLE_REQUIRED"
        if not os.access(path, os.X_OK):
            return "BROWSER_EXECUTABLE_REQUIRED"
        return None

    def run(
        self,
        payload,
        directory,
        checkpoint,
        on_start=lambda _pid: None,
        *,
        timeout=180,
        grace=5,
        on_observation=None,
    ):
        reason = self.readiness()
        if reason:
            return WorkerOutcome(None, reason, False, True)
        command = [sys.executable, "-m", self.worker_module]
        # Chromium creates a Unix socket beneath TMPDIR. Linux's sockaddr_un
        # limit is shorter than an ordinary nested job path, so keep its private
        # scratch directory short while retaining HOME/evidence under the job.
        with (
            tempfile.TemporaryDirectory(prefix="browser-session-", dir=directory) as home,
            tempfile.TemporaryDirectory(
                prefix="desk-browser-", dir="/tmp" if sys.platform == "linux" else None
            ) as scratch,
        ):
            env = {
                "PATH": os.defpath,
                "HOME": home,
                "TMPDIR": scratch,
                "LANG": "C.UTF-8",
                "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=home,
                start_new_session=True,
            )
            value, error, dispatched, cleanup, forced = None, None, False, False, False
            deadline, stop_at, exited_at = time.monotonic() + timeout, None, None
            buffers = {"stdout": b"", "stderr": b""}
            total, stages = 0, 0
            selector = selectors.DefaultSelector()
            try:
                on_start(process.pid)
                request = {**payload, "directory": str(directory), "executable": self.executable}
                process.stdin.write((json.dumps(request, ensure_ascii=True) + "\n").encode())
                process.stdin.flush()
                for name in buffers:
                    stream = getattr(process, name)
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
                while process.poll() is None or selector.get_map():
                    if process.poll() is not None:
                        exited_at = exited_at or time.monotonic()
                        if time.monotonic() - exited_at > grace:
                            # A descendant can retain pipes after the leader exited. Do not
                            # signal a possibly reused PID/group; stop draining and fail closed.
                            error, forced = error or "BROWSER_CLEANUP_UNCONFIRMED", True
                            break
                    if stop_at is None:
                        try:
                            checkpoint(None)  # Privacy/session/cancel fence while the child works.
                            if time.monotonic() >= deadline:
                                raise DomainError("BROWSER_DEADLINE_EXCEEDED", 409)
                        except DomainError as exc:
                            error, stop_at = exc.code, time.monotonic()
                            if process.poll() is None:
                                # Give the Python worker a chance to close Playwright normally.
                                process.send_signal(signal.SIGTERM)
                    elif time.monotonic() - stop_at > grace and process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        forced = True
                    for key, _ in selector.select(0.05):
                        try:
                            part = os.read(key.fileobj.fileno(), 8192)
                        except BlockingIOError:
                            continue
                        if not part:
                            selector.unregister(key.fileobj)
                            continue
                        total += len(part)
                        if total > self.protocol_limit:
                            raise DomainError("BROWSER_PROTOCOL_LIMIT", 409)
                        name = key.data
                        if name == "stderr":
                            # Do not forward raw third-party browser diagnostics to the UI.
                            buffers[name] = (buffers[name] + part)[-2048:]
                            continue
                        buffers[name] += part
                        while b"\n" in buffers[name]:
                            line, buffers[name] = buffers[name].split(b"\n", 1)
                            message = json.loads(line)
                            kind = message.get("type")
                            if kind == "checkpoint":
                                stage = message.get("stage")
                                stages += 1
                                if (
                                    stage not in self.stage_names
                                    or stages > self.stage_limit
                                    or stop_at is not None
                                ):
                                    raise DomainError("BROWSER_PROTOCOL_REJECTED", 409)
                                checkpoint(stage)  # Parent journals dispatch before allowing input.
                                dispatched = dispatched or payload["operation"] == "execute"
                                process.stdin.write(b'{"allow":true}\n')
                                process.stdin.flush()
                            elif kind == "observation" and on_observation is not None:
                                try:
                                    checkpoint(None)
                                    answer = on_observation(message["value"])
                                    checkpoint(None)
                                except DomainError as exc:
                                    error, stop_at = exc.code, time.monotonic()
                                    # The interactive worker is waiting for an
                                    # instruction. Finish without another input,
                                    # then drain its close acknowledgement.
                                    answer = {
                                        "finish": True,
                                        "outcome": "needs_owner",
                                        "reason": "stopped_by_owner",
                                    }
                                encoded = (json.dumps(answer, ensure_ascii=True) + "\n").encode()
                                if len(encoded) > 32000:
                                    raise DomainError("BROWSER_PROTOCOL_LIMIT", 409)
                                process.stdin.write(encoded)
                                process.stdin.flush()
                            elif kind == "result" and value is None:
                                value = message["value"]
                            elif kind == "error":
                                code = message.get("code", "BROWSER_WORKER_FAILED")
                                error = error or (
                                    code
                                    if code
                                    in {
                                        "BROWSER_WORKER_FAILED",
                                        "BROWSER_TARGET_CHANGED",
                                        "BROWSER_DOWNLOAD_REJECTED",
                                        "BROWSER_CANCELLED",
                                        "BROWSER_PUBLIC_DNS_REQUIRED",
                                        "BROWSER_CONTENT_MISMATCH",
                                    }
                                    else "BROWSER_WORKER_FAILED"
                                )
                            elif kind == "cleanup" and message.get("closed") is True:
                                cleanup = True
                            else:
                                raise DomainError("BROWSER_PROTOCOL_REJECTED", 409)
                    if process.poll() is not None and not selector.get_map():
                        break
                if process.wait(timeout=grace) != 0 and not error:
                    error = "BROWSER_WORKER_FAILED"
            except (OSError, ValueError, KeyError, DomainError, subprocess.TimeoutExpired) as exc:
                error = exc.code if isinstance(exc, DomainError) else "BROWSER_PROTOCOL_REJECTED"
            finally:
                selector.close()
                if process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    try:
                        process.wait(timeout=grace)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=grace)
                        forced = True
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
            return WorkerOutcome(value, error, dispatched, cleanup and not forced, forced)
