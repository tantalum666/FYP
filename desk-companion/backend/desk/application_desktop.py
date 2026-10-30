"""Owned desktop supervisor used by the optional local application executor.

Runs only in the separately configured execution environment. No model key,
host home directory, reference oracle or Docker socket belongs in this image.
"""

import functools
import http.server
import json
import signal
import subprocess
import threading
import time
from uuid import uuid4
from pathlib import Path


class SourceHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; script-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_args):
        pass


def main():
    profile = Path("/home/desk/office-profile")
    browser_profile = Path("/home/desk/browser-profile")
    source = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 8765), functools.partial(SourceHandler, directory="/inputs")
    )
    threading.Thread(target=source.serve_forever, daemon=True).start()
    logfile = open("/tmp/desk-applications.log", "a")
    office = subprocess.Popen(
        [
            "/usr/bin/libreoffice",
            "-env:UserInstallation=" + profile.as_uri(),
            "--accept=pipe,name=desk-applications;urp;StarOffice.ServiceManager",
            "--nologo",
            "--nodefault",
            "--norestore",
            "--nofirststartwizard",
        ],
        stdout=logfile,
        stderr=logfile,
    )
    browser = subprocess.Popen(
        [
            "/usr/bin/chromium",
            "--user-data-dir=" + str(browser_profile),
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-background-mode",
            "--disable-extensions",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            "--window-size=1400,920",
            "about:blank",
        ],
        stdout=logfile,
        stderr=logfile,
    )
    Path("/tmp/desk-applications.json").write_text(
        json.dumps(
            {"instance_id": uuid4().hex, "office_pid": office.pid, "browser_pid": browser.pid}
        )
    )
    stopped = threading.Event()

    def stop(*_):
        stopped.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopped.wait(0.5):
        if office.poll() is not None or browser.poll() is not None:
            break
    source.shutdown()
    for process in (browser, office):
        if process.poll() is None:
            process.terminate()
    time.sleep(0.2)
    for process in (browser, office):
        if process.poll() is None:
            process.kill()
    logfile.close()


if __name__ == "__main__":
    main()
