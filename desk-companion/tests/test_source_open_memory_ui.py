"""Desktop and narrow: finding Sources → Open memory → Memory focus.

Local fake initiative + fixture login. Not live mailbox or paid model.
Owned ports 5195 (Vite) and 8836 (API).
"""

import tempfile
import os
from pathlib import Path
import re
import socket
import time

import pytest

from ui_fixture_paths import CHROME, evidence_root, compiled_fixture, stop_fixture

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = evidence_root("2026-11-25-source-open-memory")
API_PORT = 8836
WEB_PORT = API_PORT
MEMORY_BODY = "The fictional contract begins in January 2025."


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
        "from desk.app import create_app\n"
        "from desk.text_ai import TextConfig\n"
        "from desk.tasks import TaskInput\n"
        "from desk.workspace_data import PreferencesUpdate, WorkspacePreferences\n"
        "from desk.initiative import Findings\n"
        f"app = create_app({str(runtime)!r}, development_origin='http://127.0.0.1:{WEB_PORT}', password='fixture', scheduler=False)\n"
        "r = app.state.runtime\n"
        "r.text_ai.config = TextConfig(provider='fake', background=True)\n"
        "r.data.update(PreferencesUpdate(expected_version=1, preferences=WorkspacePreferences(quiet_enabled=False)), 'prefs')\n"
        f"r.memory.create({MEMORY_BODY!r}, 'fact')\n"
        "r.tasks.create(TaskInput(title='Check fictional contract dates', next_step='A draft says April 2024.'), 'task')\n"
        "def generate(system, context, schema, purpose, **kwargs):\n"
        "    refs = [s['ref'] for s in context['sources'] if s['kind'] in {'memory', 'task'}]\n"
        "    return Findings(findings=[{\n"
        "        'kind': 'conflict', 'importance': 'high',\n"
        "        'message_en': 'The contract dates differ between your saved note and the draft. Which is current?',\n"
        "        'message_zh': '保存的记录与草稿中的合同日期不同，哪一个是目前正确的？',\n"
        "        'source_refs': refs,\n"
        "    }])\n"
        "r.text_ai.generate = generate\n"
        "r.initiative.advance()\n"
        "import uvicorn\n"
        f"uvicorn.run(app, host='127.0.0.1', port={API_PORT}, log_level='warning')\n"
    )
    return compiled_fixture(seed, ROOT, env, API_PORT)


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
    open_memory = card.get_by_role(
        "button", name=re.compile(r"Open memory:\s*" + re.escape(MEMORY_BODY[:40]))
    )
    open_memory.click()
    memory = page.locator(".memory-list").first
    memory.wait_for(state="visible", timeout=15000)
    focused = page.locator(".memory-list [aria-current=true]")
    focused.wait_for(state="visible", timeout=20000)
    assert MEMORY_BODY in focused.inner_text()
    assert focused.get_attribute("data-memory-id")
    page.screenshot(path=str(shot), full_page=True)
    overflow = measure(page)
    # Finding must still be pending: reopen Conversation and see it.
    page.goto(f"{origin}/?page=assistant", wait_until="domcontentloaded")
    page.get_by_role("button", name="Conversation", exact=True).click()
    page.get_by_role("article", name="Proactive suggestion").wait_for()
    page.get_by_role("article", name="Proactive suggestion").get_by_role(
        "button", name="Got it"
    ).wait_for()
    return overflow


def test_source_open_memory_on_desktop_and_narrow():
    from playwright.sync_api import sync_playwright

    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the source-open-memory ports are unavailable")
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
