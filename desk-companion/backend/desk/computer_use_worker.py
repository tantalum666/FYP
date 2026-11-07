"""Screenshot/action worker. Fresh browser, no model key or arbitrary code input."""

import asyncio
from contextlib import ExitStack
import json
import re
import signal
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .browser_policy import canonical_https
from .computer_use_files import write_file as exclusive_write
from .browser_worker import emit, checkpoint
from .computer_use_demo import demo_server
from .computer_use_models import (
    COMPUTER_DEMOS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    origin_of,
)
from .computer_use_protocol import validate_actions, keyboard_keys
from .computer_use_observation import snapshot, same_document, scoped_storage
from .computer_use_network import local_browser_proxy, public_host
from .store import DomainError, encode

COMMIT = re.compile(
    r"place\s+(?:the\s+)?order|pay\b|buy\s+now|confirm\s+(?:purchase|booking|reservation)|submit\s+(?:order|booking)|accept\s+(?:terms|agreement)|购买|立即下单|提交订单|付款|支付|确认预订|同意.{0,5}条款",
    re.I,
)
SENSITIVE = re.compile(
    r"password|user[_ -]?name|credit.?card|card[_ -]?(?:number|no)|cc-number|cvc|cvv|one-time|otp|passport|email|e-mail|phone|address|(?:full|first|last|given|family)[_ -]?name|密码|验证码|身份证|证件|信用卡|邮箱|电话|地址|姓名|乘机人",
    re.I,
)


class Boundary:
    def __init__(self, origins, demo_origin=None, proxy=None):
        self.origins, self.demo_origin = set(origins), demo_origin
        self.checked = set()
        self.reason = None
        self.requests = 0
        self.proxy = proxy
        self.resolving = {}
        self.blocked = []
        self.document_generation = 0
        self.action_note = ""

    def track(self, page):
        def navigated(frame):
            if frame == page.main_frame:
                self.document_generation += 1
                if origin_of(frame.url) not in self.origins:
                    self.reason = "site_action_needs_owner"

        page.on("framenavigated", navigated)

    async def route(self, route):
        request = route.request
        self.requests += 1
        origin = origin_of(request.url)
        allowed = request.method in {"GET", "HEAD"} and self.requests <= 500
        if origin == self.demo_origin:
            pass
        else:
            allowed = allowed and canonical_https(request.url) is not None
            if allowed and origin not in self.checked:
                try:
                    if origin not in self.resolving:
                        self.resolving[origin] = asyncio.create_task(
                            asyncio.to_thread(
                                public_host, urlsplit(request.url).hostname, self.proxy
                            )
                        )
                    await self.resolving[origin]
                    self.checked.add(origin)
                except Exception:
                    allowed = False
        if request.is_navigation_request():
            allowed = allowed and origin in self.origins and request.frame.parent_frame is None
        if not allowed:
            if len(self.blocked) < 5:
                self.blocked.append(
                    {
                        "method": request.method,
                        "origin": origin[:180],
                        "resource": request.resource_type,
                        "navigation": request.is_navigation_request(),
                    }
                )
            # Block background writes too, but do not abort an otherwise readable
            # page merely because its analytics/bootstrap POST was rejected.
            if request.is_navigation_request() and request.frame.parent_frame is None:
                self.reason = "site_action_needs_owner"
            await route.abort()
        else:
            await route.continue_()


async def input_target(page, action):
    return await page.evaluate(
        """a => {
      let el=('x' in a)?document.elementFromPoint(a.x,a.y):document.activeElement;
      el=el?.closest('button,a,input,textarea,select,[role=button]')||el;
      return {tag:el?.tagName?.toLowerCase()||'',type:el?.getAttribute('type')||'',
      label:[el?.innerText,el?.getAttribute('aria-label'),el?.getAttribute('name'),el?.id,
        el?.getAttribute('autocomplete'),el?.labels?.[0]?.innerText].filter(Boolean).join(' ').slice(0,1200)};
    }""",
        action,
    )


async def act(page, action, check_document=lambda: None):
    kind = action["type"]
    target = await input_target(page, action)
    check_document()
    if target["type"] == "file":
        return "file_access_needs_owner"
    if kind in {"click", "double_click", "type", "keypress"}:
        if COMMIT.search(target["label"]):
            return "final_submission_needs_owner"
        if kind in {"type", "keypress"} and (
            target["type"] in {"password", "email", "tel"} or SENSITIVE.search(target["label"])
        ):
            return "personal_or_login_input_needs_owner"
    if kind == "click":
        await page.mouse.click(action["x"], action["y"], button=action["button"])
    elif kind == "double_click":
        await page.mouse.dblclick(action["x"], action["y"])
    elif kind == "move":
        await page.mouse.move(action["x"], action["y"])
    elif kind == "drag":
        first, *rest = action["path"]
        await page.mouse.move(first["x"], first["y"])
        await page.mouse.down()
        try:
            for point in rest:
                await page.mouse.move(point["x"], point["y"])
        finally:
            await page.mouse.up()
    elif kind == "scroll":
        await page.mouse.move(action["x"], action["y"])
        await page.mouse.wheel(action["scroll_x"], action["scroll_y"])
    elif kind == "keypress":
        keys = keyboard_keys(action["keys"])
        if target["tag"] == "select" and keys in {"ArrowDown", "ArrowUp", "Home", "End"}:
            # Native select popups differ across headless Mac/Linux. Apply the
            # same bounded key movement to the currently focused control and
            # emit the application's ordinary input/change events.
            options = await page.locator(":focus").evaluate(
                "el => ({current:el.selectedIndex, enabled:Array.from(el.options).map((o,i)=>o.disabled?-1:i).filter(i=>i>=0)})"
            )
            enabled = options["enabled"]
            if not enabled:
                return "input_target_needs_review"
            index = enabled.index(options["current"]) if options["current"] in enabled else 0
            index = (
                0
                if keys == "Home"
                else len(enabled) - 1
                if keys == "End"
                else min(len(enabled) - 1, index + 1)
                if keys == "ArrowDown"
                else max(0, index - 1)
            )
            await page.locator(":focus").select_option(index=enabled[index])
        elif target["tag"] == "select" and keys == "Enter":
            await page.keyboard.press("Escape")
        else:
            await page.keyboard.press(keys)
    elif kind == "type":
        if target["tag"] not in {"input", "textarea"}:
            return "input_target_needs_review"
        if target["type"] == "date" and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", action["text"]):
            await page.locator(":focus").fill(action["text"])
        else:
            await page.keyboard.insert_text(action["text"])
    elif kind == "wait":
        await asyncio.sleep(0.25)
    return None


async def run(request):
    from playwright.async_api import async_playwright

    directory = Path(request["directory"])
    job = request["intent"]
    browser, context, closed = None, None, False
    task = asyncio.current_task()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    with ExitStack() as stack:
        demo = job["start_url"] in COMPUTER_DEMOS
        counters = None
        proxy = local_browser_proxy(request.get("browser_proxy"))
        if demo:
            url, counters = stack.enter_context(demo_server(job["start_url"]))
            origins = [url]
        else:
            url, origins = job["start_url"], job["allowed_origins"]
            try:
                await asyncio.to_thread(public_host, urlsplit(url).hostname, proxy)
            except Exception:
                # No browser launch has been attempted at this point.
                exclusive_write(
                    directory,
                    "navigation.json",
                    encode(
                        {
                            "stage": "initial_page",
                            "http_status": None,
                            "network_error": "PUBLIC_DNS_UNAVAILABLE",
                            "origin": origin_of(url),
                            "blocked": [],
                        }
                    ).encode(),
                )
                emit("cleanup", closed=True)
                raise DomainError("BROWSER_PUBLIC_DNS_REQUIRED", 409) from None
        boundary = Boundary(origins, url if demo else None, proxy)
        storage = None
        if request.get("resume_state"):
            storage = json.loads((directory / "source-state.json").read_text())
            if demo:
                for entry in storage.get("origins", []):
                    entry["origin"] = url  # Same fictional app, new owned listener.
            storage = scoped_storage(storage, boundary.origins)
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=request["executable"],
                    headless=True,
                    chromium_sandbox=True,
                    proxy={"server": proxy} if proxy and not demo else None,
                    args=[
                        "--disable-quic",
                        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                    ]
                    + (["--disable-http2"] if request.get("http1_only") is True else []),
                    timeout=30000,
                )
                context = await browser.new_context(
                    viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                    device_scale_factor=1,
                    accept_downloads=False,
                    service_workers="block",
                    permissions=[],
                    storage_state=storage,
                )
                context.set_default_timeout(10000)
                await context.route("**/*", boundary.route)
                await context.route_web_socket("**/*", lambda ws: ws.close())

                async def extra_page(page):
                    if len(context.pages) > 1:
                        boundary.reason = "new_window_needs_owner"
                        await page.close()

                context.on("page", extra_page)
                page = await context.new_page()

                boundary.track(page)
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.on("download", lambda _: setattr(boundary, "reason", "download_needs_owner"))
                await checkpoint("computer_open")
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as error:
                    network = re.search(r"net::ERR_[A-Z0-9_]+", str(error))
                    exclusive_write(
                        directory,
                        "navigation.json",
                        encode(
                            {
                                "stage": "initial_page",
                                "http_status": None,
                                "network_error": network.group()
                                if network
                                else "NAVIGATION_FAILED",
                                "origin": origin_of(url),
                                "blocked": boundary.blocked,
                            }
                        ).encode(),
                    )
                    raise DomainError("BROWSER_TARGET_CHANGED", 409) from None
                if not response or response.status >= 400:
                    exclusive_write(
                        directory,
                        "navigation.json",
                        encode(
                            {
                                "stage": "initial_page",
                                "http_status": response.status if response else None,
                                "network_error": None,
                                "origin": origin_of(url),
                                "blocked": boundary.blocked,
                            }
                        ).encode(),
                    )
                    raise DomainError("BROWSER_TARGET_CHANGED", 409)
                if boundary.reason:
                    exclusive_write(
                        directory,
                        "navigation.json",
                        encode(
                            {
                                "stage": "initial_page",
                                "http_status": response.status,
                                "network_error": "NAVIGATION_REQUIRES_REVIEW",
                                "origin": origin_of(url),
                                "blocked": boundary.blocked,
                            }
                        ).encode(),
                    )
                    raise DomainError("BROWSER_TARGET_CHANGED", 409)
                outcome, reason, observation = "step_limit", "step_limit", None
                for sequence in range(1, job["max_steps"] + 1):
                    try:
                        current_observation = await snapshot(page, directory, sequence, boundary)
                    except DomainError:
                        if observation is None:
                            exclusive_write(
                                directory,
                                "navigation.json",
                                encode(
                                    {
                                        "stage": "initial_page",
                                        "http_status": None,
                                        "network_error": "DOCUMENT_CHANGED_DURING_OBSERVATION",
                                        "origin": origin_of(url),
                                    }
                                ).encode(),
                            )
                            raise
                        outcome, reason = (
                            "needs_owner",
                            boundary.reason or "page_changed_before_observation",
                        )
                        break
                    observation = current_observation
                    if boundary.reason:
                        outcome, reason = "needs_owner", boundary.reason
                        break
                    emit("observation", value=observation)
                    raw = await asyncio.to_thread(sys.stdin.buffer.readline, 32001)
                    if not raw.endswith(b"\n"):
                        raise ValueError("Incomplete computer command")
                    command = json.loads(raw)
                    if command.get("finish") is True:
                        outcome = command.get("outcome", "review_ready")
                        if outcome not in {"review_ready", "needs_owner"}:
                            raise ValueError("Unexpected finish state")
                        reason = command.get("reason", "review_prepared_page")
                        if outcome == "review_ready" and not same_document(
                            page, boundary, observation
                        ):
                            outcome, reason = "needs_owner", "page_changed_before_input"
                        break
                    if not same_document(page, boundary, observation):
                        if origin_of(page.url) not in boundary.origins:
                            outcome, reason = "needs_owner", "page_changed_before_input"
                            break
                        boundary.action_note = "The previous input batch was not executed because the document navigated. Inspect the new page."
                        continue
                    if command.get("observation") != sequence:
                        raise ValueError("Stale computer observation")
                    applied = 0
                    boundary.action_note = ""
                    for action in validate_actions(command.get("actions")):
                        await checkpoint("computer_action")
                        if not same_document(page, boundary, observation):
                            boundary.action_note = f"Applied {applied} inputs before navigation; remaining inputs were not executed."
                            if origin_of(page.url) not in boundary.origins:
                                boundary.reason = "site_action_needs_owner"
                            break

                        def document_guard():
                            if not same_document(page, boundary, observation):
                                raise DomainError("BROWSER_TARGET_CHANGED", 409)

                        try:
                            boundary.reason = (
                                await act(page, action, document_guard) or boundary.reason
                            )
                        except DomainError:
                            boundary.action_note = f"Applied {applied} inputs before navigation; remaining inputs were not executed."
                            if origin_of(page.url) not in boundary.origins:
                                boundary.reason = "site_action_needs_owner"
                            break
                        if boundary.reason:
                            break
                        applied += 1
                    if boundary.reason:
                        if origin_of(page.url) in boundary.origins:
                            try:
                                observation = await snapshot(
                                    page, directory, sequence + 1, boundary
                                )
                            except DomainError:
                                pass  # Keep only the last admitted observation.
                        outcome, reason = "needs_owner", boundary.reason
                        break
                else:
                    try:
                        observation = await snapshot(
                            page, directory, job["max_steps"] + 1, boundary
                        )
                    except DomainError:
                        outcome, reason = "needs_owner", "page_changed_before_observation"
                state = scoped_storage(await context.storage_state(), boundary.origins)
                exclusive_write(directory, "browser-state.json", encode(state).encode())
                value = {
                    "observation": observation,
                    "outcome": outcome,
                    "reason": reason,
                    "browser_version": browser.version,
                    "sandbox_requested": True,
                    "network_boundary": "public_request_routing_only",
                    "demo": demo,
                    "demo_submissions": counters["submissions"] if counters else None,
                }
                await context.close()
                context = None
                await browser.close()
                browser = None
                closed = True
        finally:
            if context:
                await asyncio.wait_for(context.close(), 5)
            if browser:
                await asyncio.wait_for(browser.close(), 5)
            if context or browser:
                closed = True
            if closed:
                emit("cleanup", closed=True)
        emit("result", value=value)


def main():
    try:
        line = sys.stdin.buffer.readline(128 * 1024)
        if not line.endswith(b"\n"):
            raise ValueError("Incomplete worker request")
        asyncio.run(run(json.loads(line)))
    except (asyncio.CancelledError, KeyboardInterrupt):
        emit("error", code="BROWSER_CANCELLED")
        return 1
    except Exception as error:
        emit(
            "error", code=error.code if isinstance(error, DomainError) else "BROWSER_WORKER_FAILED"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
