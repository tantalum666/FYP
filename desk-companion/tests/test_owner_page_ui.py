"""Desktop and narrow-card checks for the live local page handoff."""

import os
import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from playwright.sync_api import sync_playwright

from desk.app import create_app
from desk.text_ai import TextConfig

CHROME = "/usr/local/bin/google-chrome"
ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not os.access(CHROME, os.X_OK), reason="local Chrome is required")


def _descendants(pid):
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().split(")")[-1].split()
            command = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except (OSError, IndexError, ValueError):
            continue
        if int(fields[1]) == pid:
            child = int(entry.name)
            found.append((child, command))
            found.extend(_descendants(child))
    return found


def test_hold_card_on_desktop_and_narrow_screen(tmp_path):
    seen = []
    app = create_app(tmp_path, password="fixture", scheduler=True)
    runtime = app.state.runtime
    runtime.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "synthetic-key"
    )
    runtime.text_ai.transport = httpx.MockTransport(
        lambda request: seen.append(request.url)
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
    runtime.jobs.computer_use.enabled = True
    runtime.jobs.computer_use.supervisor.executable = CHROME
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8831, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 20
    while not server.started:
        if time.monotonic() > deadline:
            raise AssertionError("API did not start")
        time.sleep(0.05)
    vite = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5190", "--strictPort"],
        cwd=ROOT / "frontend",
        env={**os.environ, "DESK_API_TARGET": "http://127.0.0.1:8831"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto("http://127.0.0.1:5190/", wait_until="domcontentloaded")
            page.get_by_role("button", name="To do").wait_for(timeout=30000)
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
            card = page.locator(".assistant-action-card")
            assert card.locator("text=Waiting for you").count() >= 1
            assert page.evaluate(
                """() => {
                  const card = document.querySelector(".assistant-action-card");
                  return card.scrollWidth <= card.clientWidth + 1;
                }"""
            )
            page.get_by_role("button", name="Take over").click()
            page.get_by_label("Type on this page").wait_for(timeout=15000)
            page.get_by_role("button", name="Hand back").wait_for()
            page.set_viewport_size({"width": 320, "height": 740})
            page.wait_for_timeout(300)
            assert page.evaluate(
                """() => {
                  const card = document.querySelector(".owner-page-controls");
                  const doc = document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1;
                  return doc && card && card.scrollWidth <= card.clientWidth + 1;
                }"""
            )
            worker = runtime.jobs.computer_use.supervisor.live_page
            assert worker is not None
            for child, command in _descendants(worker.channel.process.pid):
                if "chrome" in command.lower():
                    os.kill(child, 9)
            page.locator(".error-message", has_text="The page closed").wait_for(timeout=20000)
            page.get_by_role("button", name="Check result").wait_for()
            assert seen == []
            page.goto("http://127.0.0.1:5190/?page=tasks", wait_until="domcontentloaded")
            page.get_by_role("button", name="Work & tools").click()
            assert page.get_by_role("button", name="Work & tools").get_attribute("aria-expanded") == "true"
            browser.close()
    finally:
        vite.terminate()
        vite.wait(timeout=10)
        server.should_exit = True
