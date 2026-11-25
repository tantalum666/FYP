"""Desktop and narrow-card checks for the live local page handoff."""

import os
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest

expect = pytest.importorskip("playwright.sync_api").expect
import uvicorn
from playwright.sync_api import sync_playwright

from desk.app import create_app
from desk.text_ai import TextConfig

from ui_fixture_paths import (
    CHROME,
    evidence_root,
    process_children as _descendants,
    wait_for_fixture,
)

ROOT = Path(__file__).resolve().parents[1]
API_PORT = 8852
WEB_PORT = API_PORT
pytestmark = pytest.mark.skipif(not os.access(CHROME, os.X_OK), reason="local Chrome is required")


def _free(port):
    with socket.socket() as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def _wait_port_free(port, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _free(port):
            return True
        time.sleep(0.05)
    return _free(port)


def test_hold_card_on_desktop_and_narrow_screen(tmp_path):
    if not _free(API_PORT) or not _free(WEB_PORT):
        pytest.fail(
            f"owner-page ports {API_PORT}/{WEB_PORT} are already taken; "
            "refusing to attach to another worker's servers"
        )
    seen = []
    app = create_app(
        tmp_path,
        development_origin=f"http://127.0.0.1:{WEB_PORT}",
        password="fixture",
        scheduler=True,
    )
    runtime = app.state.runtime
    runtime.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    runtime.text_ai.transport = httpx.MockTransport(
        lambda request: (
            seen.append(request.url)
            or httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "The page is open."}],
                        }
                    ],
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                },
            )
        )
    )
    runtime.jobs.computer_use.enabled = True
    runtime.jobs.computer_use.supervisor.executable = CHROME
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=API_PORT, log_level="error"))
    api_thread = threading.Thread(target=server.run, daemon=True)
    api_thread.start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            server.should_exit = True
            raise AssertionError("API did not start")
        if not api_thread.is_alive() and not server.started:
            raise AssertionError("API thread exited before the server started")
        time.sleep(0.05)
    wait_for_fixture(API_PORT)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{WEB_PORT}/", wait_until="domcontentloaded")
            page.get_by_role("button", name="Tasks").wait_for(timeout=30000)
            assert page.locator("textarea").count() >= 1
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1"
            )
            prepared = page.evaluate(
                """async () => {
                  const headers = {"Content-Type":"application/json","X-Desk-Request":"1"};
                  const prepared = await fetch("/api/computer/computer-use/jobs", {
                    method:"POST", headers:{...headers,"X-Operation-Id":"ui-prepare"},
                    body: JSON.stringify({action:"computer_use", engine:"local", title:"Check the rehearsal page",
                      goal:"Stop if a password is required", start_url:"demo:verification",
                      public_only:true, share_screen:true, max_steps:2})
                  });
                  const body = await prepared.json();
                  if (!prepared.ok) return {ok:false, status:prepared.status, body};
                  const loaded = await fetch(`/api/computer/jobs/${body.job.id}`, {headers});
                  const job = (await loaded.json()).job;
                  const approved = await fetch(`/api/computer/jobs/${job.id}/approve`, {
                    method:"POST", headers:{...headers,"X-Operation-Id":"ui-approve"},
                    body: JSON.stringify({expected_version:job.version, intent_hash:job.intent_hash})
                  });
                  return {ok:approved.ok, status:approved.status, id:job.id, body: await approved.json()};
                }"""
            )
            assert prepared["ok"], prepared
            page.get_by_role("button", name="More assistant options").click()
            page.get_by_role("button", name="Computer actions & activity").click()
            page.get_by_role("button", name="Take over").wait_for(timeout=30000)
            activity = page.locator(
                "section.assistant-secondary:not([hidden]) article.assistant-action-card"
            )
            expect(activity).to_have_count(1, timeout=15000)
            expect(activity.locator("text=Waiting for you")).to_have_count(1, timeout=15000)
            assert page.evaluate(
                """() => {
                  const card = document.querySelector("section.assistant-secondary:not([hidden]) .assistant-action-card");
                  return !!card && card.scrollWidth <= card.clientWidth + 1;
                }"""
            )
            page.get_by_role("button", name="Take over").click()
            # Paused and held cards share state-owner_takeover. The typing
            # control is rendered only after this panel reloads the held phase.
            held = page.locator(
                "section.assistant-secondary:not([hidden]) article.assistant-action-card.state-owner_takeover"
            )
            typing = held.get_by_label("Type on this page")
            hand_back = held.get_by_role("button", name="Hand back")
            typing.wait_for(timeout=15000)
            hand_back.wait_for()
            expect(held).to_have_count(1, timeout=15000)
            assert typing.is_visible()
            assert hand_back.is_visible()
            chat = page.locator(
                "section.assistant-chat[hidden] article.assistant-action-card.state-owner_takeover"
            )
            expect(chat).to_have_count(1, timeout=15000)
            shots = evidence_root("browser-artifacts")
            shots.mkdir(parents=True, exist_ok=True)
            qa = evidence_root("2026-11-24-owner-page-handoff")
            qa.mkdir(parents=True, exist_ok=True)
            held.screenshot(path=str(shots / "owner-hold-desktop.png"))
            held.screenshot(path=str(qa / "desktop-hold.png"))
            page.set_viewport_size({"width": 320, "height": 740})
            page.wait_for_timeout(300)
            assert page.evaluate(
                """() => {
                  const card = document.querySelector("section.assistant-secondary:not([hidden]) .owner-page-controls");
                  const width = document.documentElement.clientWidth;
                  const doc = document.documentElement.scrollWidth <= width + 1;
                  if (!card) return false;
                  const rect = card.getBoundingClientRect();
                  return doc && rect.width > 0 && rect.right <= width + 1 && card.scrollWidth <= card.clientWidth + 1;
                }"""
            )
            held.screenshot(path=str(shots / "owner-hold-narrow.png"))
            held.screenshot(path=str(qa / "narrow-hold.png"))
            worker = runtime.jobs.computer_use.supervisor.live_page
            assert worker is not None
            for child, command in _descendants(worker.channel.process.pid):
                if "chrome" in command.lower():
                    os.kill(child, 9)
            visible = page.locator("section.assistant-secondary:not([hidden])")
            visible.locator(".error-message", has_text="The page closed").wait_for(timeout=20000)
            visible.get_by_role("button", name="Check result").wait_for()
            page.get_by_role("button", name="Back to chat").click()
            conversation = page.get_by_label("Conversation", exact=True)
            conversation.locator(".error-message", has_text="The page closed").wait_for(
                timeout=15000
            )
            expect(conversation.get_by_label("Type on this page")).to_have_count(0, timeout=15000)
            expect(conversation.get_by_role("button", name="Take over")).to_have_count(
                0, timeout=15000
            )
            assert seen == []
            # Stay on the connected page. Reloading here waits on the session
            # read while the closed browser is still draining, so the tasks
            # list is opened from the navigation that is already on screen.
            page.get_by_role("button", name="Back to Alice").click()
            page.get_by_role("button", name="More", exact=True).click()
            page.get_by_role("button", name="Tasks", exact=True).click()
            tools = page.get_by_role("button", name="Work & tools")
            tools.wait_for(timeout=15000)
            tools.click()
            assert (
                page.get_by_role("button", name="Work & tools").get_attribute("aria-expanded")
                == "true"
            )
            browser.close()
    finally:
        server.should_exit = True
        api_thread.join(timeout=10)
        assert _wait_port_free(API_PORT), f"API port {API_PORT} still held after owned cleanup"
