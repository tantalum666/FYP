"""Desktop and narrow: Inbox calendar update → View calendar.

Fixture-published notice + login. Not live Google, mailbox, or paid model.
Owned ports 5203 (Vite) and 8844 (API).
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
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-inbox-calendar-view"
API_PORT = 8844
WEB_PORT = 5203


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
        "from datetime import datetime, timezone\n"
        "from desk.app import create_app\n"
        "from desk.notify import Notice\n"
        "clock = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)\n"
        f"app = create_app({str(runtime)!r}, password='fixture', clock=lambda: clock, scheduler=False)\n"
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
    assert view.count() == 1
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
        api = web = None
        try:
            api, web = start_servers(Path(f"/tmp/inbox-calendar-view-ui-{width}"))
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
