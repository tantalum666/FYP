"""Desktop and narrow: Inbox calendar update → View calendar.

Fixture-published notice + login. Not live Google, mailbox, or paid model.
Owned ports 5203 (Vite) and 8844 (API).
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
EVIDENCE = evidence_root("2026-11-25-inbox-calendar-view")
API_PORT = 8844
WEB_PORT = API_PORT


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
    seed = (
        "from datetime import datetime, timezone\n"
        "from desk.app import create_app\n"
        "from desk.notify import Notice\n"
        "clock = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)\n"
        f"app = create_app({str(runtime)!r}, development_origin='http://127.0.0.1:{WEB_PORT}', password='fixture', clock=lambda: clock, scheduler=False)\n"
        "r = app.state.runtime\n"
        "r.notify.publish(Notice("
        "'calendar-deadline-fixture-1', 'calendar_deadline', "
        "'Calendar update', '日程更新', "
        "'A saved deadline is approaching for a local fixture event.', "
        "'本地样例日程的截止时间临近。', "
        "'A saved deadline is approaching for a local fixture event.', "
        "'本地样例日程的截止时间临近。'"
        "), quiet=False)\n"
        "assert any(n.get('kind') == 'calendar_deadline' and n.get('state') == 'open' "
        "for n in r.notify.listing()['notices'])\n"
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
    inbox.get_by_role("button").filter(has_text="Calendar update").click()
    view = inbox.get_by_role("button", name="View calendar", exact=True)
    expect(view).to_have_count(1, timeout=15000)
    view.click()
    surface = page.locator(".calendar-surface").first
    surface.wait_for(state="visible", timeout=15000)
    assert "page=calendar" in page.url
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    notices = page.request.get(
        f"{origin}/api/notices?open_only=true",
        headers={"X-Desk-Request": "1"},
    )
    assert notices.ok, notices.text()
    items = notices.json().get("notices") or []
    assert any(item.get("kind") == "calendar_deadline" for item in items)
    return overflow


def test_inbox_calendar_view_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the inbox-calendar-view ports are unavailable")
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
