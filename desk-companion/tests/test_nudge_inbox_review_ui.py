"""Desktop and narrow: Inbox evening check-in → View tasks.

Rule-based nudge + fixture login. Not live mailbox or paid model.
Owned ports 5197 (Vite) and 8838 (API).
"""

import tempfile
import os
from pathlib import Path
import socket
import time

import pytest

expect = pytest.importorskip("playwright.sync_api").expect

from ui_fixture_paths import CHROME, evidence_root, compiled_fixture, stop_fixture

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = evidence_root("2026-11-25-nudge-inbox-review")
API_PORT = 8838
WEB_PORT = API_PORT
TASK_TITLE = "Finish fictional evening report"


def free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def measure(page):
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          return { page: doc.scrollWidth - doc.clientWidth };
        }"""
    )


def start_servers(runtime: Path):
    runtime.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    # 13:00 UTC ≈ 21:00 HKT — evening_check window with quiet off.
    seed = (
        "from datetime import datetime, timezone\n"
        "from desk.app import create_app\n"
        "from desk.tasks import TaskInput\n"
        "from desk.workspace_data import PreferencesUpdate, WorkspacePreferences\n"
        "clock = datetime(2026, 10, 2, 13, 0, tzinfo=timezone.utc)\n"
        f"app = create_app({str(runtime)!r}, development_origin='http://127.0.0.1:{WEB_PORT}', password='fixture', clock=lambda: clock, scheduler=False)\n"
        "r = app.state.runtime\n"
        f"r.tasks.create(TaskInput(title={TASK_TITLE!r}, next_step='Draft the summary.'), 'task')\n"
        "r.data.update(PreferencesUpdate(expected_version=1, preferences=WorkspacePreferences("
        "quiet_enabled=False, evening_check_enabled=True, daily_brief_enabled=False"
        ")), 'prefs')\n"
        "r.tick()\n"
        "import uvicorn\n"
        f"uvicorn.run(app, host='127.0.0.1', port={API_PORT}, log_level='warning')\n"
    )
    return compiled_fixture(seed, ROOT, env, API_PORT)


def run_journey(page, origin, shot):
    page.goto(f"{origin}/?page=inbox", wait_until="domcontentloaded")
    login = page.request.post(
        f"{origin}/api/session",
        data='{"username":"owner","password":"fixture"}',
        headers={"Content-Type": "application/json", "X-Desk-Request": "1"},
    )
    assert login.ok, login.text()
    page.reload(wait_until="domcontentloaded")
    inbox = page.get_by_label("Alice updates")
    inbox.wait_for(timeout=30000)
    inbox.get_by_role("button").filter(has_text="Evening check-in").click()
    view = inbox.get_by_role("button", name="View tasks", exact=True)
    expect(view).to_have_count(1, timeout=15000)
    view.click()
    tasks = page.locator(".task-panel").first
    tasks.wait_for(state="visible", timeout=15000)
    assert page.get_by_role("heading", name="Tasks", exact=True).count() >= 1
    tasks.get_by_text(TASK_TITLE, exact=True).first.wait_for(state="visible", timeout=20000)
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    # Receipt stays open (View did not dismiss).
    notices = page.request.get(
        f"{origin}/api/notices?open_only=true",
        headers={"X-Desk-Request": "1"},
    )
    assert notices.ok, notices.text()
    items = notices.json().get("notices") or []
    assert any(item.get("kind") == "evening_check" for item in items)
    return overflow


def test_nudge_inbox_review_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the nudge-inbox-review ports are unavailable")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{WEB_PORT}"
    overflows = []
    for width, height, shot in (
        (1440, 1000, EVIDENCE / "desktop-1440.png"),
        (320, 740, EVIDENCE / "narrow-320.png"),
    ):
        api = None
        try:
            api = start_servers(Path(tempfile.mkdtemp(prefix="fyp-ui-")))
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
            if api is not None:
                stop_fixture(api)
            deadline = time.time() + 10
            while time.time() < deadline and not (free(API_PORT) and free(WEB_PORT)):
                time.sleep(0.2)
    assert all(item["page"] <= 1 for item in overflows)
