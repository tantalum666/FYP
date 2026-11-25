"""Desktop and narrow: Inbox memory follow-up → View memories.

Owner-approved memory follow-up + fixture login. Not live mailbox or paid model.
Owned ports 5202 (Vite) and 8843 (API).
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
EVIDENCE = evidence_root("2026-11-25-inbox-memory-followup")
API_PORT = 8843
WEB_PORT = API_PORT
MEMORY_BODY = "Fictional dentist visit on Thursday"


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
        "from uuid import uuid4\n"
        "from desk.app import create_app\n"
        "from desk.memory_followups import FollowUpApprove\n"
        "clock = [datetime(2026, 11, 9, 16, 0, tzinfo=timezone.utc)]\n"
        f"app = create_app({str(runtime)!r}, development_origin='http://127.0.0.1:{WEB_PORT}', password='fixture', clock=lambda: clock[0], scheduler=False)\n"
        "r = app.state.runtime\n"
        f"mem = r.memory.create({MEMORY_BODY!r}, uuid4().hex)['memory']\n"
        "r.memory_followups.approve(FollowUpApprove("
        "memory_id=mem['id'], memory_version=mem['version'], "
        "due_local='2026-11-10T08:00', timezone='Asia/Hong_Kong'"
        "), uuid4().hex)\n"
        "clock[0] = datetime(2026, 11, 10, 0, 30, tzinfo=timezone.utc)\n"
        "r.tick()\n"
        "notices = [n for n in r.notify.listing()['notices'] "
        "if n.get('kind') == 'memory_followup' and n.get('state') == 'open']\n"
        "assert notices, 'expected an open memory_followup notice'\n"
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
    inbox.get_by_role("button").filter(has_text="Alice remembered").click()
    view = inbox.get_by_role("button", name="View memories", exact=True)
    expect(view).to_have_count(1, timeout=15000)
    view.click()
    memory = page.get_by_label("Memory", exact=True)
    memory.wait_for(state="visible", timeout=15000)
    fact = memory.get_by_text(MEMORY_BODY, exact=True).first
    fact.wait_for(state="visible", timeout=20000)
    assert MEMORY_BODY in memory.inner_text()
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    notices = page.request.get(
        f"{origin}/api/notices?open_only=true",
        headers={"X-Desk-Request": "1"},
    )
    assert notices.ok, notices.text()
    items = notices.json().get("notices") or []
    assert any(item.get("kind") == "memory_followup" for item in items)
    return overflow


def test_inbox_memory_followup_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the inbox-memory-followup ports are unavailable")
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
