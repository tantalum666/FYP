"""Screenshot/action worker. Fresh browser, no model key or arbitrary code input."""

import asyncio
from contextlib import ExitStack
import hashlib
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
    MAX_SCREEN_BYTES,
    origin_of,
)
from .computer_use_protocol import validate_actions, keyboard_keys
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
            if request.method not in {"GET", "HEAD"} or request.is_navigation_request():
                self.reason = "site_action_needs_owner"
            await route.abort()
        else:
            await route.continue_()


async def snapshot(page, directory, sequence, boundary):
    await checkpoint("computer_observe")
    if origin_of(page.url) not in boundary.origins:
        raise DomainError("BROWSER_TARGET_CHANGED", 409)
    screen = await page.screenshot(type="png", full_page=False)
    if len(screen) > MAX_SCREEN_BYTES:
        raise ValueError("Screen exceeds the bounded image size")
    name = f"screen-{sequence}.png"
    exclusive_write(directory, name, screen)
    # Fixed observation code, never caller/model JavaScript. Values of form
    # fields are deliberately omitted; sensitive entry is a handoff boundary.
    controls = await page.locator("button,input,select,a").evaluate_all("""elements => elements.slice(0,80).map(el => {
      const r=el.getBoundingClientRect(); return {tag:el.tagName.toLowerCase(),
      label:(el.getAttribute('aria-label')||el.labels?.[0]?.innerText||el.innerText||el.getAttribute('placeholder')||'').slice(0,120),
      x:r.x+r.width/2,y:r.y+r.height/2,visible:r.width>0&&r.height>0&&r.y>=0&&r.bottom<=innerHeight};
    }).filter(x=>x.visible).slice(0,40)""")
    return {
        "sequence": sequence,
        "screen": name,
        "sha256": hashlib.sha256(screen).hexdigest(),
        "width": SCREEN_WIDTH,
        "height": SCREEN_HEIGHT,
        "platform": sys.platform,
        "url": page.url[:2000],
        "title": (await page.title())[:300],
        "text": (await page.locator("body").inner_text())[:6000],
        "controls": controls,
        "blocked_reason": boundary.reason,
    }


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


async def act(page, action):
    kind = action["type"]
    target = await input_target(page, action)
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
                emit("cleanup", closed=True)
                raise
        boundary = Boundary(origins, url if demo else None, proxy)
        storage = None
        if request.get("resume_state"):
            storage = json.loads((directory / "source-state.json").read_text())
            if demo:
                for entry in storage.get("origins", []):
                    entry["origin"] = url  # Same fictional app, new owned listener.
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
                    ],
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
                page.on("dialog", lambda dialog: dialog.dismiss())
                page.on("download", lambda _: setattr(boundary, "reason", "download_needs_owner"))
                await checkpoint("computer_open")
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if not response or response.status >= 400:
                    raise DomainError("BROWSER_TARGET_CHANGED", 409)
                outcome, reason, observation = "step_limit", "step_limit", None
                for sequence in range(1, job["max_steps"] + 1):
                    observation = await snapshot(page, directory, sequence, boundary)
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
                        break
                    if command.get("observation") != sequence:
                        raise ValueError("Stale computer observation")
                    for action in validate_actions(command.get("actions")):
                        await checkpoint("computer_action")
                        if origin_of(page.url) not in boundary.origins:
                            boundary.reason = "site_action_needs_owner"
                            break
                        boundary.reason = await act(page, action) or boundary.reason
                        if boundary.reason:
                            break
                    if boundary.reason:
                        observation = await snapshot(page, directory, sequence + 1, boundary)
                        outcome, reason = "needs_owner", boundary.reason
                        break
                else:
                    observation = await snapshot(page, directory, job["max_steps"] + 1, boundary)
                state = await context.storage_state()
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
