"""Desktop and narrow: finding Sources → Open calendar → Event details.

Local fake initiative + fixture login. Not live mailbox or paid model.
Owned ports 5193 (Vite) and 8834 (API).
"""

import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

import pytest

CHROME = "/usr/local/bin/google-chrome"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-source-open-calendar"
API_PORT = 8834
WEB_PORT = 5193
EVENT_TITLE = "Fictional vendor visit"
# Fixed clock: 25 Nov 2026 10:00 HKT. Event tomorrow afternoon, within 7-day evidence.
CLOCK = "datetime(2026, 11, 25, 2, 0, tzinfo=timezone.utc)"
START_LOCAL = "2026-11-26T14:00"
END_LOCAL = "2026-11-26T15:00"


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
        "from desk.text_ai import TextConfig\n"
        "from desk.schemas import CreateEvents, EventInput\n"
        "from desk.workspace_data import PreferencesUpdate, WorkspacePreferences\n"
        "from desk.initiative import Findings\n"
        f"app = create_app({str(runtime)!r}, password='fixture', clock=lambda: {CLOCK}, scheduler=False)\n"
        "r = app.state.runtime\n"
        "r.text_ai.config = TextConfig(provider='fake', background=True)\n"
        "r.data.update(PreferencesUpdate(expected_version=1, preferences=WorkspacePreferences(quiet_enabled=False)), 'prefs')\n"
        f"event = EventInput(title={EVENT_TITLE!r}, start_local={START_LOCAL!r}, end_local={END_LOCAL!r})\n"
        "ident = r.store.create(CreateEvents(event=event), 'cal')['event_ids'][0]\n"
        "open('" + str(runtime / "event-id.txt") + "', 'w').write(ident)\n"
        "def generate(system, context, schema, purpose, **kwargs):\n"
        "    refs = [s['ref'] for s in context['sources'] if s['kind'] == 'calendar' and not s['ref'].startswith('calendar:google:')]\n"
        "    return Findings(findings=[{\n"
        "        'kind': 'deadline', 'importance': 'high',\n"
        "        'message_en': 'Your saved visit is tomorrow afternoon. Confirm the time before you travel.',\n"
        "        'message_zh': '已保存的拜访在明天下午，出发前请确认时间。',\n"
        "        'source_refs': refs[:1],\n"
        "    }])\n"
        "r.text_ai.generate = generate\n"
        "r.initiative.advance()\n"
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
    page.get_by_role("button", name="Conversation", exact=True).click()
    card = page.get_by_role("article", name="Proactive suggestion")
    card.wait_for(timeout=30000)
    card.get_by_text("Sources").click()
    open_cal = card.get_by_role(
        "button", name=re.compile(r"Open calendar:\s*" + re.escape(EVENT_TITLE))
    )
    open_cal.click()
    dialog = page.get_by_role("dialog")
    dialog.wait_for(state="visible", timeout=15000)
    assert EVENT_TITLE in dialog.inner_text()
    assert "Event details" in dialog.inner_text() or dialog.get_by_role(
        "heading", name=EVENT_TITLE
    ).count()
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    dialog.get_by_role("button", name="Close").click()
    # Finding must still be pending: reopen Conversation and see it.
    page.goto(f"{origin}/?page=assistant", wait_until="domcontentloaded")
    page.get_by_role("button", name="Conversation", exact=True).click()
    page.get_by_role("article", name="Proactive suggestion").wait_for()
    assert page.get_by_role("button", name="Got it").count() == 1
    return overflow


def test_source_open_calendar_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the source-open-calendar ports are unavailable")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{WEB_PORT}"
    overflows = []
    for width, height, shot in (
        (1440, 1000, EVIDENCE / "desktop-1440.png"),
        (320, 740, EVIDENCE / "narrow-320.png"),
    ):
        api = web = None
        try:
            api, web = start_servers(Path(f"/tmp/source-open-calendar-ui-{width}"))
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
