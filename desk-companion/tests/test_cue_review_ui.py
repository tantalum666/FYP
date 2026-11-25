"""Desktop and narrow browser: home initiative cue → Conversation Sources.

Local fake initiative + fixture login. Not live mailbox or paid model.
Owned ports 5210 (Vite) and 8850 (API).
"""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest

CHROME = "/usr/local/bin/google-chrome"
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-cue-review"
API_PORT = 8850
WEB_PORT = 5210


def free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.fixture(scope="module")
def servers(tmp_path_factory):
    if not Path(CHROME).exists() or not free(API_PORT) or not free(WEB_PORT):
        pytest.skip("local Chrome or the cue-review ports are unavailable")
    runtime = tmp_path_factory.mktemp("cue-review-ui")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    seed = (
        "from desk.app import create_app\n"
        "from desk.text_ai import TextConfig\n"
        "from desk.tasks import TaskInput\n"
        "from desk.workspace_data import PreferencesUpdate, WorkspacePreferences\n"
        "from desk.initiative import Findings\n"
        f"app = create_app({str(runtime)!r}, password='fixture', scheduler=False)\n"
        "r = app.state.runtime\n"
        "r.text_ai.config = TextConfig(provider='fake', background=True)\n"
        "r.data.update(PreferencesUpdate(expected_version=1, preferences=WorkspacePreferences(quiet_enabled=False)), 'prefs')\n"
        "r.memory.create('The fictional contract begins in January 2025.', 'fact')\n"
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
    api = subprocess.Popen(
        [sys.executable, "-c", seed],
        cwd=ROOT,
        env=env,
        start_new_session=True,
    )
    web = subprocess.Popen(
        [
            "npx",
            "vite",
            "--host",
            "127.0.0.1",
            "--port",
            str(WEB_PORT),
            "--strictPort",
        ],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": f"http://127.0.0.1:{API_PORT}"},
        start_new_session=True,
    )
    try:
        wait("127.0.0.1", API_PORT)
        wait("127.0.0.1", WEB_PORT)
        # Fail fast if listeners are not ours.
        for port, process in ((API_PORT, api), (WEB_PORT, web)):
            if process.poll() is not None:
                raise RuntimeError(f"server on {port} exited early: {process.returncode}")
        yield
    finally:
        for process in (web, api):
            try:
                os.killpg(process.pid, 15)
            except ProcessLookupError:
                process.terminate()
        for process in (web, api):
            process.wait(timeout=10)


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


def test_home_cue_opens_conversation_sources_on_desktop_and_narrow(servers):
    from playwright.sync_api import sync_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    origin = f"http://127.0.0.1:{WEB_PORT}"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROME,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
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
        assert cue.get_by_role("button", name="Got it").count() == 1
        cue.get_by_role("button", name="View in conversation").click()
        card = page.get_by_role("article", name="Proactive suggestion")
        card.wait_for(timeout=15000)
        assert "Sources" in card.inner_text()
        card.get_by_text("Sources").click()
        body = card.inner_text().lower()
        assert "contract" in body or "草稿" in card.inner_text()
        # Opening Conversation must not have dismissed the finding.
        assert card.get_by_role("button", name="Got it").count() == 1
        page.screenshot(path=str(EVIDENCE / "desktop-1440.png"), full_page=True)
        wide = measure(page)

        page.set_viewport_size({"width": 320, "height": 740})
        page.goto(f"{origin}/?page=assistant", wait_until="domcontentloaded")
        cue = page.get_by_label("Alice check-in")
        cue.wait_for(timeout=30000)
        cue.get_by_role("button", name="View in conversation").click()
        card = page.get_by_role("article", name="Proactive suggestion")
        card.wait_for()
        card.get_by_text("Sources").click()
        card.evaluate("node => node.scrollIntoView({block: 'center'})")
        page.screenshot(path=str(EVIDENCE / "narrow-320.png"), full_page=True)
        narrow = measure(page)
        browser.close()
    assert wide["page"] <= 1 and narrow["page"] <= 1
