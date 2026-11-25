"""Desktop and narrow recovery for an interrupted task file. No live account."""

import os
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from desk.app import create_app
from desk.computer import LocalNotesExecutor

from test_text_conversation_scope import owner_client, send

CHROME = "/usr/local/bin/google-chrome"
ROOT = Path(__file__).resolve().parents[1]
# Dedicated ports: do not share 5190/8831 with the owner-page UI harness.
API_PORT = 8833
WEB_PORT = 5192
pytestmark = pytest.mark.skipif(not os.access(CHROME, os.X_OK), reason="local Chrome is required")


class ProcessCrash(BaseException):
    pass


class CrashAfterWrite(LocalNotesExecutor):
    def execute(self, request, checkpoint):
        super().execute(request, checkpoint)
        raise ProcessCrash()


def _free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _listening_pids(port):
    inodes = set()
    for family in ("tcp", "tcp6"):
        try:
            lines = Path(f"/proc/net/{family}").read_text().splitlines()
        except OSError:
            continue
        for line in lines[1:]:
            parts = line.split()
            local, state, inode = parts[1], parts[3], parts[9]
            if state == "0A" and int(local.rsplit(":", 1)[-1], 16) == port:
                inodes.add(inode)
    found = set()
    if not inodes:
        return found
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            descriptors = list((entry / "fd").iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                found.add(int(entry.name))
                break
    return found


def _descendants(pid):
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().split(")")[-1].split()
            command = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except (OSError, IndexError, ValueError):
            continue
        if int(fields[1]) == pid:
            child = int(entry.name)
            found.append((child, command))
            found.extend(_descendants(child))
    return found


def _wait_port_free(port, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _free(port):
            return True
        time.sleep(0.05)
    return _free(port)


def test_interrupted_task_explains_the_unknown_result_without_writing_again(tmp_path):
    if not _free(API_PORT) or not _free(WEB_PORT):
        pytest.fail(
            f"task-recovery ports {API_PORT}/{WEB_PORT} are already taken; "
            "refusing to attach to another worker's servers"
        )
    os.environ["DESK_COMPUTER_ENABLED"] = "1"
    first = create_app(tmp_path, password="fixture", scheduler=False)
    client = owner_client(first)
    selected = client.post(
        "/api/tasks",
        json={
            "title": "Fixture review",
            "next_step": "Read the saved file",
            "follow_up_enabled": False,
            "steps": [{"title": "Gather the notes", "done": True}],
        },
        headers={"X-Desk-Request": "1", "X-Operation-Id": "ui-task"},
    ).json()["task"]
    other = client.post(
        "/api/tasks",
        json={
            "title": "Fixture review",
            "next_step": "Leave this one alone",
            "follow_up_enabled": False,
        },
        headers={"X-Desk-Request": "1", "X-Operation-Id": "ui-other"},
    ).json()["task"]
    text = "Fixture review\nLocal rehearsal only."
    response = send(client, "Save note: " + text, task_id=selected["id"], key="ui-prepare")
    job_id = response.json()["job"]["id"]
    job = client.get(f"/api/computer/jobs/{job_id}").json()["job"]
    path = first.state.runtime.jobs.executor.root / (job_id + ".txt")
    approval = {"expected_version": job["version"], "intent_hash": job["intent_hash"]}
    client.post(
        f"/api/computer/jobs/{job_id}/approve",
        json=approval,
        headers={"X-Desk-Request": "1", "X-Operation-Id": "ui-approve"},
    )
    first.state.runtime.jobs.executor = CrashAfterWrite(tmp_path)
    with pytest.raises(ProcessCrash):
        first.state.runtime.jobs.run_one()
    written = path.stat().st_mtime_ns
    app = create_app(tmp_path, password="fixture", scheduler=False)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=API_PORT, log_level="error"))
    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            server.should_exit = True
            raise AssertionError("API did not start")
        if not api_thread.is_alive() and not server.started:
            raise AssertionError("API thread exited before the server started")
        time.sleep(0.05)
    vite = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": f"http://127.0.0.1:{API_PORT}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    page_log = []

    def _drain_page_server():
        assert vite.stdout is not None
        for line in vite.stdout:
            page_log.append(line.rstrip())
            del page_log[:-40]

    threading.Thread(target=_drain_page_server, daemon=True).start()
    ready = time.monotonic() + 20
    while time.monotonic() < ready:
        if vite.poll() is not None:
            server.should_exit = True
            raise AssertionError(
                f"The page server exited before it was ready ({vite.returncode}): {' | '.join(page_log[-5:])}"
            )
        family = {vite.pid, *(child for child, _command in _descendants(vite.pid))}
        owners = _listening_pids(WEB_PORT)
        if owners and owners <= family:
            break
        time.sleep(0.05)
    else:
        server.should_exit = True
        try:
            os.killpg(vite.pid, signal.SIGTERM)
        except OSError:
            vite.terminate()
        raise AssertionError(f"The page server did not become ready on {WEB_PORT}")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{WEB_PORT}/?page=tasks", wait_until="domcontentloaded")
            page.get_by_role("button", name="Read the saved file").wait_for(timeout=30000)
            page.get_by_role("button", name="Read the saved file").click()
            page.get_by_text("The saved result is unknown").wait_for(timeout=15000)
            page.get_by_role("button", name="Discuss this task").wait_for()
            assert page.get_by_text("No new file was written").count() == 0
            assert page.get_by_role("checkbox", name="Gather the notes").is_checked()
            shots = Path("/opt/cursor/artifacts")
            shots.mkdir(parents=True, exist_ok=True)
            qa = ROOT.parent / "output/qa/2026-11-25-task-recovery"
            qa.mkdir(parents=True, exist_ok=True)
            card = page.locator("section.task-job-results")
            card.screenshot(path=str(shots / "task-recovery-desktop.png"))
            card.screenshot(path=str(qa / "desktop-recovery.png"))
            page.set_viewport_size({"width": 320, "height": 740})
            page.wait_for_timeout(300)
            assert page.evaluate(
                """() => {
                  const card = document.querySelector(".task-recovery-unknown");
                  const width = document.documentElement.clientWidth;
                  if (!card) return false;
                  const rect = card.getBoundingClientRect();
                  return document.documentElement.scrollWidth <= width + 1
                    && rect.width > 0 && rect.right <= width + 1;
                }"""
            )
            card.screenshot(path=str(shots / "task-recovery-narrow.png"))
            card.screenshot(path=str(qa / "narrow-recovery.png"))
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_role("button", name="Discuss this task").click()
            page.get_by_role("button", name="More assistant options").click()
            page.get_by_role("button", name="Computer actions & activity").click()
            page.get_by_role("button", name="Check result").wait_for(timeout=20000)
            page.get_by_role("button", name="Check result").click()
            page.get_by_text("Verified").wait_for(timeout=20000)
            assert path.stat().st_mtime_ns == written
            # Force a fresh document load so the task list is not left under the
            # discuss overlay from the same ?page=tasks URL.
            page.goto(
                f"http://127.0.0.1:{WEB_PORT}/?page=tasks&recovery=list",
                wait_until="domcontentloaded",
            )
            page.get_by_role("button", name="Leave this one alone").wait_for(timeout=30000)
            page.get_by_role("button", name="Leave this one alone").click()
            page.get_by_text("No file actions are linked yet.").wait_for(timeout=15000)
            assert page.get_by_text("The saved result is unknown").count() == 0
            assert other["id"] != selected["id"]
            browser.close()
    finally:
        try:
            os.killpg(vite.pid, signal.SIGTERM)
        except OSError:
            vite.terminate()
        try:
            vite.wait(timeout=10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(vite.pid, signal.SIGKILL)
            except OSError:
                vite.kill()
            vite.wait(timeout=5)
        server.should_exit = True
        api_thread.join(timeout=10)
        assert _wait_port_free(WEB_PORT), f"page port {WEB_PORT} still held after owned cleanup"
        assert _wait_port_free(API_PORT), f"API port {API_PORT} still held after owned cleanup"
