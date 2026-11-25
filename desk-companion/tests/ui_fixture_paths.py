"""Local paths for the real-browser UI regressions."""

import os
from pathlib import Path
import shutil
import tempfile

CHROME = (
    os.environ.get("DESK_TEST_CHROME")
    or shutil.which("google-chrome")
    or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)


def evidence_root(name):
    configured = os.environ.get("DESK_TEST_EVIDENCE")
    base = Path(configured) if configured else Path(tempfile.gettempdir()) / "fyp-ui-evidence"
    return base / name


def process_children(parent):
    """Return only descendants of the privately owned worker under test."""
    import sys

    if sys.platform == "darwin":
        import ctypes

        lib = ctypes.CDLL("/usr/lib/libproc.dylib")

        def children(pid):
            ids = (ctypes.c_int * 512)()
            if lib.proc_listchildpids(pid, ids, ctypes.sizeof(ids)) <= 0:
                return []
            found = []
            for child in ids:
                if child <= 0:
                    continue
                path = ctypes.create_string_buffer(4096)
                lib.proc_pidpath(child, path, ctypes.sizeof(path))
                found.append((child, os.fsdecode(path.value)))
            return found
    else:

        def children(pid):
            base = Path("/proc")
            try:
                ids = (base / str(pid) / "task" / str(pid) / "children").read_text().split()
            except OSError:
                return []
            rows = []
            for child in ids:
                try:
                    rows.append(
                        (
                            int(child),
                            os.fsdecode((base / child / "cmdline").read_bytes()).replace(
                                chr(0), " "
                            ),
                        )
                    )
                except OSError:
                    continue
            return rows

    def descendants(pid):
        found = []
        for child, command in children(pid):
            found.append((child, command))
            found.extend(descendants(child))
        return found

    return descendants(parent)


def wait_for_fixture(port, *, process=None):
    import socket
    import time

    limit = time.monotonic() + 30
    while time.monotonic() < limit:
        if process and process.poll() is not None:
            raise RuntimeError("The isolated fixture exited during startup")
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"The isolated fixture did not start on {port}")


def stop_fixture(process):
    import signal
    import subprocess

    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def compiled_fixture(seed, root, env, port):
    import subprocess
    import sys

    if not (root / "frontend/dist/index.html").is_file():
        subprocess.run(["npm", "run", "build"], cwd=root / "frontend", check=True)
    process = subprocess.Popen(
        [sys.executable, "-c", seed], cwd=root, env=env, start_new_session=True
    )
    try:
        wait_for_fixture(port, process=process)
    except BaseException:
        stop_fixture(process)
        raise
    return process
