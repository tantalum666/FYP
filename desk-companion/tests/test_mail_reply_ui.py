"""Desktop and narrow browser check for the followed-reply card.

Uses the local mail sample through the real page. It is not a live mailbox.
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
EVIDENCE = ROOT.parents[0] / "output/qa/2026-11-25-followed-reply"


def free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


@pytest.fixture(scope="module")
def servers(tmp_path_factory):
    if not Path(CHROME).exists() or not free(8832) or not free(5191):
        pytest.skip("local Chrome or the reminder ports are unavailable")
    runtime = tmp_path_factory.mktemp("mail-reply-ui")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    api = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import uvicorn; from desk.app import create_app; "
            f"uvicorn.run(create_app({str(runtime)!r}, password='fixture', scheduler=False), "
            "host='127.0.0.1', port=8832, log_level='warning')",
        ],
        cwd=ROOT,
        env=env,
        start_new_session=True,
    )
    web = subprocess.Popen(
        ["npx", "vite", "--host", "127.0.0.1", "--port", "5191", "--strictPort"],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": "http://127.0.0.1:8832"},
        start_new_session=True,
    )
    try:
        wait("127.0.0.1", 8832)
        wait("127.0.0.1", 5191)
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
    deadline = time.time() + 30
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise RuntimeError(f"{host}:{port} did not open")


def test_followed_reply_card_on_desktop_and_narrow_screen(servers):
    from playwright.sync_api import sync_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROME,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto("http://127.0.0.1:5191/?page=tasks", wait_until="domcontentloaded")
        page.get_by_role("button", name="Work & tools").wait_for()
        page.get_by_role("button", name="Work & tools").click()
        page.get_by_role("button", name="Follow").first.click()
        page.get_by_text("Following").first.wait_for()
        page.get_by_role("button", name="Simulate a reply").click()
        card = page.get_by_role("article", name="Followed email reminder")
        card.wait_for()
        assert card.count() == 1
        assert "Local mail sample" in card.inner_text()
        assert "Draft a reply" in card.inner_text()
        assert card.get_by_role("textbox").count() == 0
        card.get_by_role("button", name="Read the message").click()
        card.get_by_text("Friday after 3 still works for me.").wait_for()
        assert "Not saved as a memory" in card.inner_text()
        card.get_by_role("button", name="Draft a reply").click()
        card.get_by_role("textbox").wait_for()
        card.get_by_role("button", name="Review draft").click()
        card.get_by_role("button", name="Save draft").click()
        card.get_by_text("Draft saved. Nothing was sent.").wait_for()
        card.get_by_role("button", name="Save draft").wait_for(state="hidden")
        page.screenshot(path=str(EVIDENCE / "desktop-1440.png"), full_page=True)
        wide = measure(page)
        page.set_viewport_size({"width": 320, "height": 740})
        card = page.get_by_role("article", name="Followed email reminder")
        card.wait_for()
        card.evaluate("node => node.scrollIntoView({block: 'center'})")
        page.screenshot(path=str(EVIDENCE / "narrow-320.png"), full_page=True)
        narrow = measure(page)
        browser.close()
    assert wide["card"] <= 1 and narrow["card"] <= 1
    assert wide["page"] <= 1 and narrow["page"] <= 1


def measure(page):
    return page.evaluate(
        """() => {
          const card = document.querySelector('.mail-reply-reminder');
          const doc = document.documentElement;
          return {
            card: card ? card.scrollWidth - card.clientWidth : 999,
            page: doc.scrollWidth - doc.clientWidth,
          };
        }"""
    )
