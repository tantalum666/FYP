"""Private fixed-protocol worker for real public-page / StackEdit UI interaction.

No evaluate(), model-selected locator, shell, personal profile, extension or login.
Selectors are sourced from benweet/stackedit commit 6dce2a5e36b755a0c244522b48a06c91a2df0f59;
their live-site compatibility is a separate acceptance gate, never assumed from tests.
"""

import asyncio
import hashlib
import json
import os
import signal
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path

from .browser_policy import (
    ADAPTER,
    CATALOG_VERSION,
    MAX_EXPORT_BYTES,
    STACKEDIT_URL,
    BrowserIntent,
    BrowserReceipt,
    digest,
    exclusive_write,
    request_allowed,
    require_public_dns,
    source_entry,
)
from .store import DomainError, encode


def emit(kind, **values):
    print(json.dumps({"type": kind, **values}, ensure_ascii=True), flush=True)


async def checkpoint(stage):
    emit("checkpoint", stage=stage)
    line = await asyncio.to_thread(sys.stdin.buffer.readline, 256)
    if not line or json.loads(line) != {"allow": True}:
        raise DomainError("BROWSER_CANCELLED", 409)


class PageBoundary:
    """Defense in depth only; Chromium DNS/egress is not hard-confined by this."""

    def __init__(self, source_id=None, destination=False):
        self.source_id, self.destination = source_id, destination
        self.blocked = 0
        self.violation = False
        self.requests = 0

    async def route(self, route):
        request = route.request
        self.requests += 1
        navigation = request.is_navigation_request()
        allowed = self.requests <= 200 and request_allowed(
            request.url,
            request.method,
            source_id=self.source_id,
            destination=self.destination,
            navigation=navigation,
        )
        if navigation and request.frame.parent_frame is not None:
            allowed = False
        if request.redirected_from is not None:
            allowed = False
        if not allowed:
            self.blocked += 1
            self.violation |= navigation or self.requests > 200
            await route.abort()
        else:
            await route.continue_()

    def check(self, page):
        expected = STACKEDIT_URL if self.destination else source_entry(self.source_id)["url"]
        if self.violation or page.url != expected:
            raise DomainError("BROWSER_TARGET_CHANGED", 409)


async def observe(page, boundary, source_id):
    await checkpoint("read_source")
    url = source_entry(source_id)["url"]
    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    boundary.check(page)
    if not response or response.status != 200:
        raise DomainError("BROWSER_TARGET_CHANGED", 409)
    heading = (await page.locator("h1").first.inner_text()).strip()[:300]
    # Read one observed paragraph, not an implied full-document extraction.
    excerpt = (await page.locator("div.body section > p").first.inner_text()).strip()[:1800]
    title = (await page.title()).strip()[:300]
    boundary.check(page)
    if not heading or not title or not excerpt:
        raise DomainError("BROWSER_TARGET_CHANGED", 409)
    data = {
        "source_id": source_id,
        "url": url,
        "title": title,
        "heading": heading,
        "excerpt": excerpt,
    }
    return {**data, "sha256": digest(data), "observed_at": datetime.now(UTC).isoformat()}


async def export_in_stackedit(page, boundary, request, directory):
    intent = BrowserIntent.model_validate(request["intent"])
    if digest(intent.model_dump()) != request["intent_hash"]:
        raise DomainError("BROWSER_TARGET_CHANGED", 409)
    expected_filename = intent.document_name + ".md"
    downloads, export_window = [], False

    async def download_arrived(download):
        downloads.append(download)
        if not export_window or len(downloads) != 1:
            await download.cancel()
            boundary.violation = True

    page.on("download", download_arrived)

    async def action(stage, callback):
        boundary.check(page)
        await checkpoint(stage)
        boundary.check(page)
        await callback()

    await checkpoint("open_editor")
    response = await page.goto(STACKEDIT_URL, wait_until="domcontentloaded", timeout=30000)
    boundary.check(page)
    if not response or response.status != 200 or "StackEdit" not in await page.title():
        raise DomainError("BROWSER_TARGET_CHANGED", 409)
    editor = page.locator(".editor__inner[contenteditable=true]")
    await editor.wait_for(state="visible", timeout=30000)
    tour = page.locator(".tour").get_by_role("button", name="Skip", exact=True)
    if await tour.count() and await tour.is_visible():
        await action("dismiss_tour", tour.click)
    new_file = page.locator("button.side-title__button--new-file")
    if not await new_file.is_visible():
        await action(
            "open_explorer", page.locator("button.navigation-bar__button--explorer-toggler").click
        )
    await action("new_file", new_file.click)
    name = page.locator(".explorer-node__new-child input")
    await action("name_file", lambda: name.fill(intent.document_name))
    await action("confirm_file", lambda: name.press("Enter"))
    from playwright.async_api import expect

    await expect(page.locator("input.navigation-bar__title--input")).to_have_value(
        intent.document_name, timeout=10000
    )
    await action("fill_editor", lambda: editor.fill(intent.content))
    await expect(editor).to_have_text(intent.content, timeout=10000)
    await action("open_menu", page.locator("button.navigation-bar__button--stackedit").click)
    await action("open_export", page.locator("a.menu-entry").filter(has_text="Import/export").click)
    export_link = page.locator("a.menu-entry").filter(has_text="Export as Markdown")
    boundary.check(page)
    await checkpoint("export")
    boundary.check(page)
    export_window = True
    async with page.expect_download(timeout=15000) as pending:
        await export_link.click()
    download = await pending.value
    export_window = False
    if download.suggested_filename != expected_filename or not download.url.startswith(
        "blob:https://stackedit.io/"
    ):
        await download.cancel()
        raise DomainError("BROWSER_DOWNLOAD_REJECTED", 409)
    path = await download.path()  # Actual browser-produced download, never synthesized content.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_EXPORT_BYTES:
            raise DomainError("BROWSER_DOWNLOAD_REJECTED", 409)
        body = stream.read(MAX_EXPORT_BYTES + 1)
    boundary.check(page)
    if len(downloads) != 1 or body != intent.content.encode("utf-8"):
        raise DomainError("BROWSER_CONTENT_MISMATCH", 409)
    exclusive_write(directory, "export.md", body)
    return {
        "verified": True,
        "adapter": ADAPTER,
        "catalog_version": CATALOG_VERSION,
        "job_id": intent.job_id,
        "execution_id": request["execution_id"],
        "intent_hash": request["intent_hash"],
        "source_sha256": intent.source.sha256,
        "environment_id": intent.environment_id,
        "destination": STACKEDIT_URL,
        "document_name": intent.document_name,
        "sha256": hashlib.sha256(body).hexdigest(),
        "byte_count": len(body),
        "download_count": 1,
        "export_method": "stackedit_ui_markdown_download",
        "sandbox_requested": True,
        "network_boundary": "routing_only",
        "data_scope": "public_synthetic_only",
    }


async def run(request):
    from playwright.async_api import async_playwright

    if request.get("operation") not in {"observe", "execute"}:
        raise ValueError("Unknown operation")
    source_entry(request["source_id"])
    directory = Path(request["directory"])
    if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink():
        raise ValueError("Invalid owned directory")
    destination = request["operation"] == "execute"
    require_public_dns("stackedit.io" if destination else "docs.python.org")
    browser, context, value, closed = None, None, None, False
    loop, task = asyncio.get_running_loop(), asyncio.current_task()
    loop.add_signal_handler(signal.SIGTERM, task.cancel)
    boundary = PageBoundary(request["source_id"], destination)
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    executable_path=request["executable"],
                    headless=True,
                    chromium_sandbox=True,
                    timeout=30000,
                )
                context = await browser.new_context(
                    accept_downloads=destination,
                    service_workers="block",
                    permissions=[],
                    locale="en-US",
                    viewport={"width": 1280, "height": 900},
                )
                context.set_default_timeout(10000)
                await context.route("**/*", boundary.route)
                await context.route_web_socket("**/*", lambda ws: ws.close())

                async def extra_page(page):
                    if len(context.pages) > 1:
                        boundary.violation = True
                        await page.close()

                context.on("page", extra_page)
                page = await context.new_page()
                page.on("dialog", lambda dialog: dialog.dismiss())
                if destination:
                    value = await export_in_stackedit(page, boundary, request, directory)
                    value["browser_version"] = browser.version
                else:
                    value = await observe(page, boundary, request["source_id"])
            finally:
                if context:
                    await asyncio.wait_for(context.close(), 5)
                if browser:
                    await asyncio.wait_for(browser.close(), 5)
                closed = True
    finally:
        # No successful receipt is persisted until normal context/browser cleanup completed.
        if closed:
            emit("cleanup", closed=True)
    if destination:
        value["browser_close_confirmed"] = True
        value = BrowserReceipt.model_validate(value).model_dump()
        exclusive_write(directory, "receipt.json", encode(value).encode())
    emit("result", value=value)


def main():
    try:
        line = sys.stdin.buffer.readline(128 * 1024)
        if not line.endswith(b"\n"):
            raise ValueError("Incomplete command")
        asyncio.run(run(json.loads(line)))
    except (asyncio.CancelledError, KeyboardInterrupt):
        emit("error", code="BROWSER_CANCELLED")
        return 1
    except Exception as exc:
        emit("error", code=exc.code if isinstance(exc, DomainError) else "BROWSER_WORKER_FAILED")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
