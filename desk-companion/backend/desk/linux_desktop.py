"""One approved Linux editor -> browser workflow; no arbitrary GUI/shell tool."""

import contextlib
import json
import os
import platform
import signal
import subprocess
import time
from pathlib import Path

from .computer import (
    ExecutionRejected,
    artifact_filename,
    MAX_BYTES,
    exclusive_write,
    open_real_directory,
    read_artifact,
)


class LinuxDesktopExecutor:
    identity = "linux_editor_browser_v1"
    scope = "owned_mousepad_chromium_notes_only"

    def __init__(self, runtime_directory):
        self.root = Path(runtime_directory) / "linux-workflows"
        self.enabled = os.environ.get("DESK_LINUX_DESKTOP_ENABLED") == "1"
        self.evidence = {}

    def status(self):
        ready = (
            self.enabled
            and platform.system() == "Linux"
            and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
            and bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS"))
            and all(
                Path(p).is_file()
                for p in (
                    "/usr/bin/mousepad",
                    "/usr/bin/chromium",
                    "/usr/lib/python3/dist-packages/pyatspi/__init__.py",
                    "/usr/lib/python3/dist-packages/websockets/__init__.py",
                )
            )
        )
        return {
            "enabled": self.enabled,
            "ready": ready,
            "apps": ["Mousepad", "Chromium"],
            "scope": self.scope,
        }

    def execute(self, job, checkpoint):
        if job["action"] not in {"linux_note_preview", "verify_linux_file"}:
            raise ExecutionRejected("COMPUTER_ACTION_DENIED", 403)
        if not self.status()["ready"]:
            raise ExecutionRejected("LINUX_DESKTOP_UNAVAILABLE", 409)
        filename = artifact_filename(job)
        content = job["content"].encode("utf-8")
        if len(content) > MAX_BYTES:
            raise ExecutionRejected("COMPUTER_CONTENT_TOO_LARGE", 422)
        root_fd = open_real_directory(self.root, create=True)
        try:
            checkpoint()
            if job["action"] == "verify_linux_file":
                return
            exclusive_write(root_fd, filename, b"")
        finally:
            os.close(root_fd)
        # From the empty reservation onward cancellation is an uncertain result,
        # never an assertion that nothing was written.
        try:
            self.evidence[job["artifact_id"]] = self.run_bridge(job, checkpoint)
        except Exception as error:
            raise RuntimeError("LINUX_WORKFLOW_INCOMPLETE") from error

    def run_bridge(self, job, checkpoint):
        # Do not pass API keys or the backend environment into desktop processes.
        allowed = {
            "PATH",
            "HOME",
            "USER",
            "DISPLAY",
            "WAYLAND_DISPLAY",
            "XDG_RUNTIME_DIR",
            "DBUS_SESSION_BUS_ADDRESS",
            "XAUTHORITY",
            "XDG_SESSION_TYPE",
        }
        env = {key: value for key, value in os.environ.items() if key in allowed}
        env.update(
            LANG="C.UTF-8",
            LC_ALL="C.UTF-8",
            NO_AT_BRIDGE="0",
            GTK_MODULES="atk-bridge",
            GSETTINGS_BACKEND="memory",
        )
        helper = Path(__file__).with_name("linux_desktop_bridge.py")
        target = self.root / artifact_filename(job)
        process = subprocess.Popen(
            ["/usr/bin/python3", str(helper), str(target)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
        try:
            process.stdin.write(job["content"].encode("utf-8"))
            process.stdin.close()
            end = time.monotonic() + 35
            while process.poll() is None:
                checkpoint()
                if time.monotonic() >= end:
                    raise TimeoutError("Linux workflow timeout")
                time.sleep(0.05)
            output = process.stdout.read(16385)
            if process.returncode != 0 or len(output) > 16384:
                raise RuntimeError("Linux workflow failed")
            result = json.loads(output)
            if result != {"editor_saved": True, "browser_text_matches": True}:
                raise RuntimeError("Linux workflow lacks evidence")
            return result
        except BaseException:
            # Kill only the fresh process group created for this approved job.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=1)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            raise
        finally:
            process.stdout.close()

    def verify(self, job):
        directory = open_real_directory(self.root, create=False)
        try:
            receipt = read_artifact(
                directory,
                artifact_filename(job),
                job["content"].encode("utf-8"),
                self.identity,
                self.scope,
            )
        finally:
            os.close(directory)
        if receipt["verified"] and job["action"] == "linux_note_preview":
            if self.evidence.get(job["artifact_id"]) != {
                "editor_saved": True,
                "browser_text_matches": True,
            }:
                return {"verified": False, "reason": "workflow_incomplete"}
            receipt["apps_verified"] = ["mousepad", "chromium"]
        return receipt
