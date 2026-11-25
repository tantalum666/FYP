"""Desktop and narrow-card checks for the live local page handoff."""

import os
import signal
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


def _listening_pids(port):
    inodes = set()
    for family in ("tcp", "tcp6"):
        try:
            lines = Path(f"/proc/net/{family}").read_text().splitlines()
        except OSError:
            continue
        for line in lines[1:]:
            parts = line.split()
            local, state, inode = parts[1], parts[3], parts[9]
            if state == "0A" and int(local.rsplit(":", 1)[-1], 16) == port:
                inodes.add(inode)
    found = set()
    if not inodes:
        return found
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            descriptors = list((entry / "fd").iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                found.add(int(entry.name))
                break
    return found


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
        start_new_session=True,
    )
    page_log = []

    # Vite blocks once this pipe fills, and the page then never finishes loading.
    def _drain_page_server():
        assert vite.stdout is not None
        for line in vite.stdout:
            page_log.append(line.rstrip())
            del page_log[:-40]

    threading.Thread(target=_drain_page_server, daemon=True).start()
    ready = time.monotonic() + 20
    while time.monotonic() < ready:
        if vite.poll() is not None:
            raise AssertionError(
                f"The page server exited before it was ready ({vite.returncode}): {' | '.join(page_log[-5:])}"
            )
        family = {vite.pid, *(child for child, _command in _descendants(vite.pid))}
        owners = _listening_pids(5190)
        if owners and owners <= family:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("The page server did not become ready")
    if vite.poll() is not None:
        raise AssertionError("The page server exited after it claimed port 5190")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=CHROME, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto("http://127.0.0.1:5190/", wait_until="domcontentloaded")
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
            assert activity.count() == 1
            assert activity.locator("text=Waiting for you").count() == 1
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
            assert held.count() == 1
            assert typing.is_visible()
            assert hand_back.is_visible()
            chat = page.locator(
                "section.assistant-chat[hidden] article.assistant-action-card.state-owner_takeover"
            )
            assert chat.count() == 1
            shots = Path("/opt/cursor/artifacts")
            shots.mkdir(parents=True, exist_ok=True)
            qa = ROOT.parent / "output/qa/2026-11-24-owner-page-handoff"
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
            conversation.locator(".error-message", has_text="The page closed").wait_for(timeout=15000)
            assert conversation.get_by_label("Type on this page").count() == 0
            assert conversation.get_by_role("button", name="Take over").count() == 0
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
            assert page.get_by_role("button", name="Work & tools").get_attribute("aria-expanded") == "true"
            browser.close()
    finally:
        try:
            os.killpg(vite.pid, signal.SIGTERM)
        except OSError:
            vite.terminate()
        vite.wait(timeout=10)
        server.should_exit = True
