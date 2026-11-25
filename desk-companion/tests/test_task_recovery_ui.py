"""Desktop and narrow recovery for an interrupted task file. No live account."""

import os
import socket
import threading
import time
from pathlib import Path

import pytest

expect = pytest.importorskip("playwright.sync_api").expect
import uvicorn
from playwright.sync_api import sync_playwright

from desk.app import create_app
from desk.computer import LocalNotesExecutor

from test_text_conversation_scope import owner_client, send

from ui_fixture_paths import CHROME, evidence_root, wait_for_fixture

ROOT = Path(__file__).resolve().parents[1]
# Dedicated ports: do not share 5190/8831 with the owner-page UI harness.
API_PORT = 8833
WEB_PORT = API_PORT
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
    first = create_app(
        tmp_path,
        development_origin=f"http://127.0.0.1:{WEB_PORT}",
        password="fixture",
        scheduler=False,
    )
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
    app = create_app(
        tmp_path,
        development_origin=f"http://127.0.0.1:{WEB_PORT}",
        password="fixture",
        scheduler=False,
    )
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
    wait_for_fixture(API_PORT)
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
            expect(page.get_by_text("No new file was written")).to_have_count(0, timeout=15000)
            assert page.get_by_role("checkbox", name="Gather the notes").is_checked()
            shots = evidence_root("browser-artifacts")
            shots.mkdir(parents=True, exist_ok=True)
            qa = evidence_root("2026-11-25-task-recovery")
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
            expect(page.get_by_text("The saved result is unknown")).to_have_count(0, timeout=15000)
            assert other["id"] != selected["id"]
            browser.close()
    finally:
        server.should_exit = True
        api_thread.join(timeout=10)
        assert _wait_port_free(API_PORT), f"API port {API_PORT} still held after owned cleanup"
