"""Desktop and narrow recovery for an interrupted task file. No live account."""

import os
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
pytestmark = pytest.mark.skipif(not os.access(CHROME, os.X_OK), reason="local Chrome is required")


class ProcessCrash(BaseException):
    pass


class CrashAfterWrite(LocalNotesExecutor):
    def execute(self, request, checkpoint):
        super().execute(request, checkpoint)
        raise ProcessCrash()


def test_interrupted_task_explains_the_unknown_result_without_writing_again(tmp_path):
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
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8831, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            raise AssertionError("API did not start")
        time.sleep(0.05)
    vite = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5190", "--strictPort"],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": "http://127.0.0.1:8831"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto("http://127.0.0.1:5190/?page=tasks", wait_until="domcontentloaded")
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
            page.goto("http://127.0.0.1:5190/?page=tasks", wait_until="domcontentloaded")
            page.get_by_role("button", name="Leave this one alone").click()
            page.get_by_text("No file actions are linked yet.").wait_for(timeout=15000)
            assert page.get_by_text("The saved result is unknown").count() == 0
            assert other["id"] != selected["id"]
            browser.close()
    finally:
        vite.terminate()
        vite.wait(timeout=10)
        server.should_exit = True
