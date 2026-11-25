"""Desktop and narrow: home task cue → Open task.

Rule-based task follow-up + fixture login. Not live mailbox or paid model.
Owned ports 5200 (Vite) and 8841 (API).
"""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest

CHROME = "/usr/local/bin/google-chrome"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-home-task-open"
API_PORT = 8841
WEB_PORT = 5200
TASK_TITLE = "Finish fictional home report"


def free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def wait(host, port):
    deadline = time.time() + 40
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"{host}:{port} did not open")


def measure(page):
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          return { page: doc.scrollWidth - doc.clientWidth };
        }"""
    )


def start_servers(runtime: Path):
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    seed = (
        "from datetime import datetime, timedelta, timezone\n"
        "from desk.app import create_app\n"
        "from desk.tasks import TaskInput\n"
        "clock = [datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)]\n"
        f"app = create_app({str(runtime)!r}, password='fixture', clock=lambda: clock[0], scheduler=False)\n"
        "r = app.state.runtime\n"
        f"task = r.tasks.create(TaskInput(title={TASK_TITLE!r}, next_step='Draft three headings', interval_minutes=15), 'task')['task']\n"
        "clock[0] = clock[0] + timedelta(minutes=16)\n"
        "r.tick()\n"
        "assert r.snapshot({'kind': 'owner', 'id': 'owner'})['check_in']['kind'] == 'task'\n"
        "import uvicorn\n"
        f"uvicorn.run(app, host='127.0.0.1', port={API_PORT}, log_level='warning')\n"
    )
    api = subprocess.Popen(
        [sys.executable, "-c", seed], cwd=ROOT, env=env, start_new_session=True
    )
    web = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": f"http://127.0.0.1:{API_PORT}"},
        start_new_session=True,
    )
    wait("127.0.0.1", API_PORT)
    wait("127.0.0.1", WEB_PORT)
    for port, process in ((API_PORT, api), (WEB_PORT, web)):
        if process.poll() is not None:
            raise RuntimeError(f"server on {port} exited early: {process.returncode}")
    return api, web


def stop_servers(api, web):
    for process in (web, api):
        try:
            os.killpg(process.pid, 15)
        except ProcessLookupError:
            process.terminate()
    for process in (web, api):
        process.wait(timeout=10)


def run_journey(page, origin, shot):
    page.goto(f"{origin}/?page=assistant", wait_until="domcontentloaded")
    login = page.request.post(
        f"{origin}/api/session",
        data='{"username":"owner","password":"fixture"}',
        headers={"Content-Type": "application/json", "X-Desk-Request": "1"},
    )
    assert login.ok, login.text()
    page.reload(wait_until="domcontentloaded")
    cue = page.get_by_label("Alice check-in")
    cue.wait_for(timeout=30000)
    assert cue.get_by_role("button", name="Done").count() == 1
    assert cue.get_by_role("button", name="Still working").count() == 1
    assert cue.get_by_role("button", name="In an hour").count() == 1
    open_task = cue.get_by_role("button", name="Open task", exact=True)
    assert open_task.count() == 1
    open_task.click()
    tasks = page.locator(".task-panel").first
    tasks.wait_for(state="visible", timeout=15000)
    # Narrow hides the list heading when a detail is open; assert the selected title.
    title = tasks.locator("[data-inspect-title]")
    title.wait_for(state="visible", timeout=20000)
    assert TASK_TITLE in title.inner_text()
    assert "Draft three headings" in tasks.inner_text()
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    # Opening the task must not complete or snooze it.
    listing = page.request.get(
        f"{origin}/api/tasks",
        headers={"X-Desk-Request": "1"},
    )
    assert listing.ok, listing.text()
    body = listing.json()
    items = body.get("tasks") or body.get("items") or []
    match = next((item for item in items if item.get("title") == TASK_TITLE), None)
    assert match is not None
    assert match.get("status") != "done"
    assert not match.get("paused")
    return overflow


def test_home_task_open_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the home-task-open ports are unavailable")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{WEB_PORT}"
    overflows = []
    for width, height, shot in (
        (1440, 1000, EVIDENCE / "desktop-1440.png"),
        (320, 740, EVIDENCE / "narrow-320.png"),
    ):
        api = web = None
        try:
            api, web = start_servers(Path(f"/tmp/home-task-open-ui-{width}"))
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=CHROME,
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                page = browser.new_page(viewport={"width": width, "height": height})
                overflows.append(run_journey(page, origin, shot))
                browser.close()
        finally:
            if api and web:
                stop_servers(api, web)
            deadline = time.time() + 10
            while time.time() < deadline and not (free(API_PORT) and free(WEB_PORT)):
                time.sleep(0.2)
    assert all(item["page"] <= 1 for item in overflows)
