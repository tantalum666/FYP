#!/usr/bin/env python3
"""Actual browser navigation/capture race regression on two owned local fixtures.

No model, external website, personal profile or paid request is involved.
"""

import argparse
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk import computer_use_observation as observations
from desk.computer_use_worker import Boundary, act
from desk.store import DomainError


@contextmanager
def fixture(label):
    body = (
        "<html><style>button{width:240px;height:70px}</style><body data-clicks='0'>"
        f"<button onclick=\"document.body.dataset.clicks='1'\">{label}</button>"
        f"<script>localStorage.setItem('label','{label}')</script></body></html>"
    ).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


async def check(browser_path, report, public, outside):
    from playwright.async_api import async_playwright

    async def local_checkpoint(_):
        pass

    observations.checkpoint = local_checkpoint
    result = {"real_browser": True, "model_calls": 0}
    with tempfile.TemporaryDirectory(prefix="fyp-scope-") as scratch:
        env = {"PATH": os.defpath, "HOME": scratch, "TMPDIR": scratch, "LANG": "C.UTF-8"}
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=browser_path, headless=True, chromium_sandbox=True, env=env
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800}, service_workers="block"
            )
            page = await context.new_page()
            boundary = Boundary([public])
            boundary.track(page)
            await page.goto(public)
            before = await observations.snapshot(page, report, 1, boundary)
            await page.goto(outside)
            assert not observations.same_document(page, boundary, before)

            def guard():
                if not observations.same_document(page, boundary, before):
                    raise DomainError("BROWSER_TARGET_CHANGED", 409)

            try:
                await act(page, {"type": "click", "x": 30, "y": 30, "button": "left"}, guard)
            except DomainError:
                result["stale_input_blocked"] = True
            assert await page.locator("body").get_attribute("data-clicks") == "0"
            await page.mouse.click(30, 30)
            assert await page.locator("body").get_attribute("data-clicks") == "1"
            result["positive_control"] = True
            await page.goto(public)
            boundary.reason = None
            original = page.screenshot

            async def racing_screenshot(**kwargs):
                await page.goto(outside)
                return await original(**kwargs)

            page.screenshot = racing_screenshot
            try:
                await observations.snapshot(page, report, 2, boundary)
            except DomainError:
                result["unadmitted_capture_rejected"] = True
            finally:
                page.screenshot = original
            assert not (report / "screen-2.png").exists()
            await page.goto(public)
            boundary.reason = None
            same_url = await observations.snapshot(page, report, 3, boundary)
            await page.reload()
            assert not observations.same_document(page, boundary, same_url)
            result["same_url_reload_detected"] = True
            state = observations.scoped_storage(await context.storage_state(), boundary.origins)
            assert {x["origin"] for x in state["origins"]} == {public}
            result["unadmitted_state_removed"] = True
            await context.close()
            await browser.close()
            result["normal_close"] = True
    assert result.get("stale_input_blocked") and result.get("unadmitted_capture_rejected")
    (report / "verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.report.mkdir(parents=True, exist_ok=False)
    with fixture("Admitted page") as public, fixture("Unadmitted fixture") as outside:
        asyncio.run(check(args.chromium, args.report, public, outside))


if __name__ == "__main__":
    main()
