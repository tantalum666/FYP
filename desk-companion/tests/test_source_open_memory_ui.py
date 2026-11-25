"""Desktop and narrow: finding Sources → Open memory → Memory focus.

Local fake initiative + fixture login. Not live mailbox or paid model.
Owned ports 5195 (Vite) and 8836 (API).
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
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-source-open-memory"
API_PORT = 8836
WEB_PORT = 5195
MEMORY_BODY = "The fictional contract begins in January 2025."


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
        "from desk.app import create_app\n"
        "from desk.text_ai import TextConfig\n"
        "from desk.tasks import TaskInput\n"
        "from desk.workspace_data import PreferencesUpdate, WorkspacePreferences\n"
        "from desk.initiative import Findings\n"
        f"app = create_app({str(runtime)!r}, password='fixture', scheduler=False)\n"
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
    assert page.get_by_role("button", name="Got it").count() == 1
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
        api = web = None
        try:
            api, web = start_servers(Path(f"/tmp/source-open-memory-ui-{width}"))
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
