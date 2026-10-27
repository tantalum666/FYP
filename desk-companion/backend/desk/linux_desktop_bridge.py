"""Private helper for one fresh Mousepad instance and one Chromium profile.

The API calls this only after owner approval. It gets approved text on stdin,
never a model-generated command, URL, path or global keyboard sequence.
"""

import contextlib
import json
from urllib.request import urlopen
from urllib.parse import urlsplit
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def nodes(root, maximum=4000):
    stack = [root]
    count = 0
    while stack and count < maximum:
        node = stack.pop(0)
        count += 1
        yield node
        with contextlib.suppress(Exception):
            stack.extend(node.getChildAtIndex(i) for i in range(min(node.childCount, 500)))


def application(pyatspi, process):
    desktop = pyatspi.Registry.getDesktop(0)
    for app in desktop:
        with contextlib.suppress(Exception):
            pid = app.get_process_id()
            # Some Chromium launchers fork. The fresh owned process group is the boundary.
            if (
                pid
                and os.getpgid(pid) == os.getpgrp()
                and (pid == process.pid or "chrom" in app.name.lower())
            ):
                return app
    return None


def wait(check, timeout=10):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        result = check()
        if result:
            return result
        time.sleep(0.05)
    raise RuntimeError("DESKTOP_STEP_TIMEOUT")


def action_named(app, name):
    for node in nodes(app):
        with contextlib.suppress(Exception):
            if node.name == name and node.queryAction().nActions:
                return node.queryAction().doAction(0)
    return False


def main():
    import pyatspi

    path = Path(sys.argv[1])
    if (
        not path.is_absolute()
        or not re.fullmatch(r"[a-f0-9]{32}\.txt", path.name)
        or path.is_symlink()
    ):
        raise RuntimeError("TARGET_DENIED")
    if path.stat().st_size != 0 or path.stat().st_nlink != 1:
        raise RuntimeError("TARGET_CHANGED")
    content = sys.stdin.buffer.read(32001).decode("utf-8")
    if not content or len(content.encode()) > 32000:
        raise RuntimeError("CONTENT_DENIED")
    # Shell=False; fixed executables, own instance, and no clipboard/global keystrokes.
    editor = subprocess.Popen(
        ["/usr/bin/mousepad", "--disable-server", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    app = wait(lambda: application(pyatspi, editor))

    def edit():
        for node in nodes(app):
            with contextlib.suppress(Exception):
                if node.getState().contains(pyatspi.STATE_EDITABLE):
                    if node.queryEditableText().setTextContents(content):
                        return True
        return False

    wait(edit)
    action_named(app, "File")
    wait(lambda: action_named(app, "Save"))
    wait(lambda: path.read_bytes() == content.encode())
    profile = path.parent / (path.stem + "-browser")
    profile.mkdir(mode=0o700)
    subprocess.Popen(
        [
            "/usr/bin/chromium",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-background-mode",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            "--user-data-dir=" + str(profile),
            "--app=" + path.as_uri(),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # CDP is restricted to this new profile's random loopback port and exact
    # local text document. No caller-supplied JS, URL or existing browser profile.
    port_file = profile / "DevToolsActivePort"
    wait(lambda: port_file.is_file(), timeout=12)
    port = int(port_file.read_text().splitlines()[0])
    if not 1024 <= port <= 65535:
        raise RuntimeError("BROWSER_PORT_INVALID")

    def page_target():
        with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
            pages = json.load(response)
        return next(
            (
                page
                for page in pages
                if page.get("type") == "page" and page.get("url") == path.as_uri()
            ),
            None,
        )

    target = wait(page_target)
    url = target["webSocketDebuggerUrl"]
    parts = urlsplit(url)
    if (
        parts.scheme != "ws"
        or parts.hostname not in {"127.0.0.1", "localhost"}
        or parts.port != port
        or not parts.path.startswith("/devtools/page/")
    ):
        raise RuntimeError("BROWSER_TARGET_DENIED")
    from websockets.sync.client import connect

    expected = " ".join(content.split())
    with connect(url, open_timeout=3, max_size=128000) as socket:
        sequence = 0

        def browser_matches():
            nonlocal sequence
            sequence += 1
            socket.send(
                json.dumps(
                    {
                        "id": sequence,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "document.body ? document.body.innerText : ''",
                            "returnByValue": True,
                        },
                    }
                )
            )
            while True:
                result = json.loads(socket.recv(timeout=3))
                if result.get("id") == sequence:
                    text = result.get("result", {}).get("result", {}).get("value", "")
                    return isinstance(text, str) and " ".join(text.split()) == expected

        wait(browser_matches)
    print('{"editor_saved":true,"browser_text_matches":true}', flush=True)


if __name__ == "__main__":
    main()
