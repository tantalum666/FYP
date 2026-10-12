"""Run the standalone demo process and verify an approval → HTTP → SQLite loop.

Uses fictional data and temporary directories only. No browser, provider, hardware
or user-computer access is exercised. The test-owned subprocess is always stopped.
"""

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from desk.app import create_app  # noqa: E402
from desk.application_executor import APP_ID, canonical_origin  # noqa: E402
from desk.jobs import JobApproval, JobInput  # noqa: E402


def run(port):
    origin = canonical_origin(f"http://127.0.0.1:{port}")
    # Fail on occupied ports rather than operating another service.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    with tempfile.TemporaryDirectory(prefix="desk-application-check-") as temporary:
        base = Path(temporary)
        application_dir = base / "application"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
        with (base / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "desk.demo_application",
                    "--port",
                    str(port),
                    "--directory",
                    str(application_dir),
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 10
                with httpx.Client(trust_env=False, follow_redirects=False, timeout=1) as client:
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError("Standalone application exited before readiness")
                        try:
                            response = client.get(origin + "/api/status")
                            response.raise_for_status()
                            status = response.json()
                            if status["application"] == APP_ID:
                                break
                        except (httpx.HTTPError, ValueError, KeyError):
                            pass
                        if time.monotonic() > deadline:
                            raise TimeoutError("Standalone application readiness timeout")
                        time.sleep(0.05)
                    # Validate the live identity against this process's own DB before any write.
                    with sqlite3.connect(application_dir / "records.sqlite3") as conn:
                        assert (
                            conn.execute("SELECT value FROM identity WHERE id=1").fetchone()[0]
                            == status["instance_id"]
                        )
                        assert conn.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
                    previous = {
                        key: os.environ.get(key)
                        for key in ("DESK_COMPUTER_ENABLED", "DESK_DEMO_APP_ORIGIN")
                    }
                    try:
                        os.environ["DESK_COMPUTER_ENABLED"] = "1"
                        os.environ["DESK_DEMO_APP_ORIGIN"] = origin
                        companion = create_app(
                            base / "companion", password="fictional-fixture", scheduler=False
                        )
                    finally:
                        for key, value in previous.items():
                            if value is None:
                                os.environ.pop(key, None)
                            else:
                                os.environ[key] = value
                    jobs = companion.state.runtime.jobs
                    content = "Fictional controlled application record\n你好 · 🦉\nCommands are inert data."
                    draft = jobs.prepare(
                        JobInput(action="create_record", title="Fictional review", content=content),
                        "standalone-prepare",
                    )["job"]
                    jobs.run_one()
                    with sqlite3.connect(application_dir / "records.sqlite3") as conn:
                        before = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                    assert before == 0
                    review = jobs.detail(draft["id"], review=True)
                    jobs.approve(
                        draft["id"],
                        JobApproval(
                            expected_version=review["version"], intent_hash=review["intent_hash"]
                        ),
                        "standalone-approve",
                    )
                    jobs.run_one()
                    done = jobs.detail(draft["id"])
                    assert done["state"] == "succeeded" and done["result"]["verified"] is True
                    with sqlite3.connect(application_dir / "records.sqlite3") as conn:
                        rows = [
                            json.loads(row[0])
                            for row in conn.execute("SELECT payload FROM records")
                        ]
                    assert len(rows) == 1 and rows[0]["content"] == content
                    assert rows[0]["intent_hash"] == review["intent_hash"]
                    assert rows[0]["instance_id"] == status["instance_id"]
                    page = client.get(origin + "/")
                    assert "Fictional review" in page.text and "你好" in page.text
                    same = jobs.prepare(
                        JobInput(action="create_record", title="Fictional review", content=content),
                        "standalone-prepare",
                    )["job"]
                    assert same["id"] == draft["id"] and same["state"] == "succeeded"
                    jobs.run_one()
                    with sqlite3.connect(application_dir / "records.sqlite3") as conn:
                        after = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                    assert after == 1
                    jobs.shutdown()
                    result = {
                        "checked_at": datetime.now(UTC).isoformat(),
                        "origin": origin,
                        "interface": "real_http_application_api",
                        "standalone_process": True,
                        "application_instance_id": status["instance_id"],
                        "job_id": draft["id"],
                        "before_approval_records": before,
                        "after_approval_records": after,
                        "sqlite_independent_readback": True,
                        "repeat_draft_one_record": True,
                        "application_html_contains_record": True,
                        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                        "state": done["state"],
                        "receipt": done["result"],
                        "history": done["history"],
                        "paid_provider_calls": 0,
                        "browser_control_exercised": False,
                        "hardware_actions": 0,
                    }
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            result["test_owned_process_stopped"] = process.poll() is not None
            result["temporary_test_data_removed_on_exit"] = True
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.port)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Verified standalone application workflow; evidence: {args.output}")


if __name__ == "__main__":
    main()
