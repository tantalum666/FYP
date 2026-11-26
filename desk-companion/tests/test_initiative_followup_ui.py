"""Desktop and narrow browser check for finding → follow-up → status.

Uses the local fake initiative path. It is not a live mailbox or paid model run.
"""

import os
from pathlib import Path
import re
import socket

import pytest

expect = pytest.importorskip("playwright.sync_api").expect

from ui_fixture_paths import CHROME, evidence_root, compiled_fixture, stop_fixture

WEB_PORT = 8840
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = evidence_root("2026-11-25-initiative-followup")


def free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.fixture(scope="module")
def servers(tmp_path_factory):
    if not Path(CHROME).exists() or not free(8840) or not free(5200):
        pytest.skip("local Chrome or the follow-up ports are unavailable")
    runtime = tmp_path_factory.mktemp("initiative-followup-ui")
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
        "uvicorn.run(app, host='127.0.0.1', port=8840, log_level='warning')\n"
    )
    api = compiled_fixture(seed, ROOT, env, WEB_PORT)
    try:
        yield
    finally:
        stop_fixture(api)


def test_finding_followup_on_desktop_and_narrow_screen(servers):
    from playwright.sync_api import sync_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROME,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto("http://127.0.0.1:8840/?page=assistant", wait_until="domcontentloaded")
        # Cookie path is /api on this origin; login through the Vite proxy.
        login = page.request.post(
            "http://127.0.0.1:8840/api/session",
            data='{"username":"owner","password":"fixture"}',
            headers={"Content-Type": "application/json", "X-Desk-Request": "1"},
        )
        assert login.ok, login.text()
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="Conversation", exact=True).click()
        page.get_by_role("article", name="Proactive suggestion").wait_for(timeout=30000)
        card = page.get_by_role("article", name="Proactive suggestion")
        actions = ["Follow up on this", "Remind me later", "Got it"]
        for width in (320, 1440):
            page.set_viewport_size({"width": width, "height": 1000})
            assert_separate_targets(card, actions)
        assert "Sources" in card.inner_text()
        card.get_by_text("Sources").click()
        assert "contract" in card.inner_text().lower() or "草稿" in card.inner_text()
        # Failed follow-up path: first attempt is unknown (aborted), then exact retry.
        failed = {"count": 0}

        def fail_then_pass(route):
            if failed["count"] == 0:
                failed["count"] += 1
                # Abort leaves status 0 so the private write queue keeps the same id.
                route.abort("connectionfailed")
                return
            route.continue_()

        page.route("**/api/initiative/*/follow-ups", fail_then_pass)
        card.get_by_role("button", name="Follow up on this").click()
        page.get_by_role("alert").wait_for()
        page.get_by_role("button", name="Retry the same request").wait_for()
        page.get_by_role("button", name="Retry the same request").click()
        card.get_by_text("Follow-up open. Nothing was sent.").wait_for()
        expect(card.get_by_role("button", name="Follow up on this")).to_have_count(0, timeout=15000)
        page.screenshot(path=str(EVIDENCE / "desktop-1440.png"), full_page=True)
        wide = measure(page)
        page.goto("http://127.0.0.1:8840/?page=tasks", wait_until="domcontentloaded")
        page.get_by_role("button", name=re.compile(r"The contract dates differ")).wait_for()
        page.set_viewport_size({"width": 320, "height": 740})
        page.goto("http://127.0.0.1:8840/?page=assistant", wait_until="domcontentloaded")
        page.get_by_role("button", name="Conversation", exact=True).click()
        card = page.get_by_role("article", name="Proactive suggestion")
        card.wait_for()
        card.get_by_text("Follow-up open. Nothing was sent.").wait_for()
        card.evaluate("node => node.scrollIntoView({block: 'center'})")
        assert_separate_targets(card, actions[1:])
        page.screenshot(path=str(EVIDENCE / "narrow-320.png"), full_page=True)
        narrow = measure(page)
        card.get_by_role("button", name="Got it", exact=True).click()
        acknowledged = page.get_by_role("article", name="Acknowledged suggestion", exact=True)
        expect(acknowledged).to_contain_text("The contract dates differ")
        page.goto("http://127.0.0.1:8840/?page=assistant&conversation=open")
        page.get_by_role("button", name="More assistant options").click()
        page.get_by_role("button", name="Follow-up history", exact=True).click()
        history = page.get_by_role("region", name="Follow-up history")
        receipt = history.get_by_role("article", name="Acknowledged suggestion")
        expect(receipt).to_contain_text("The contract dates differ")
        expect(receipt.get_by_role("button", name="Got it", exact=True)).to_have_count(0)
        browser.close()
    assert wide["page"] <= 1 and narrow["page"] <= 1


def assert_separate_targets(card, names):
    frame = card.bounding_box()
    previous = None
    for name in names:
        button = card.get_by_role("button", name=name, exact=True).bounding_box()
        assert button["width"] >= 44 and button["height"] >= 44, name
        assert frame["x"] <= button["x"]
        assert button["x"] + button["width"] <= frame["x"] + frame["width"] + 1
        if previous:
            horizontal = button["x"] - (previous["x"] + previous["width"])
            vertical = button["y"] - (previous["y"] + previous["height"])
            assert horizontal >= 6 or vertical >= 6, name
        previous = button


def measure(page):
    return page.evaluate(
        """() => {
          const doc = document.documentElement;
          return { page: doc.scrollWidth - doc.clientWidth };
        }"""
    )
