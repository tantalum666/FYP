"""Exercise FYP's actual sandboxed browser adapter with one public/synthetic brief.

Requires an already provisioned Chromium executable. Installs nothing and never
changes OS security settings. The output directory must not exist. Runtime/evidence
are retained for inspection; do not publish its runtime/ directory.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from desk.app import create_app  # noqa: E402
from desk.browser_policy import BrowserApproval, BrowserJobInput, PublicObservationInput  # noqa: E402
from desk.store import DomainError  # noqa: E402


TITLE = "FYP public documentation acceptance"
NOTE = "Fictional acceptance brief. Only the displayed official public excerpt is included."


def run(executable, output, approve_fixture=False):
    output = output.expanduser().absolute()
    output.mkdir(mode=0o700)  # Exclusive new test workspace, never replace previous evidence.
    (output / ".gitignore").write_text("runtime/\n", encoding="utf-8")
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "data_scope": "public_synthetic_only",
        "network_boundary": "routing_only",
        "stackedit_live_ui_exercised": False,
        "paid_provider_calls": 0,
        "user_profile_or_credentials_used": False,
        "state": "starting",
        "acceptance_passed": False,
        "source_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "backend/desk").glob("browser_*.py"))
        },
    }
    service = None
    previous = {k: os.environ.get(k) for k in ("DESK_BROWSER_ENABLED", "DESK_BROWSER_EXECUTABLE")}
    try:
        os.environ["DESK_BROWSER_ENABLED"] = "1"
        os.environ["DESK_BROWSER_EXECUTABLE"] = str(executable.expanduser().absolute())
        password = secrets.token_urlsafe(32)  # Only this isolated application's disposable owner.
        runtime = create_app(output / "runtime", password=password, scheduler=False).state.runtime
        service = runtime.browser_jobs
        token = runtime.store.authenticate("owner", password)
        session_hash = hashlib.sha256(token.encode()).hexdigest()
        report["capabilities"] = service.capabilities()
        if not report["capabilities"]["ready"]:
            raise DomainError(report["capabilities"]["reason"], 409)
        report["playwright_version"] = importlib.metadata.version("playwright")
        observation = service.observe(
            PublicObservationInput(source_id="python_asyncio", public_only=True),
            "acceptance-source",
            session_hash=session_hash,
        )["observation"]
        payload = BrowserJobInput(
            observation_id=observation["id"], title=TITLE, note=NOTE, public_only=True
        )
        job = service.prepare(payload, "acceptance-prepare", session_hash=session_hash)["job"]
        report.update(
            observation=observation,
            preview=job["request"],
            intent_hash=job["intent_hash"],
            job_id=job["id"],
            state="review",
        )
        # Explicit review evidence is printed and persisted before any destination action.
        print(
            json.dumps(
                {
                    "destination": job["request"]["destination"],
                    "persistence": job["request"]["persistence"],
                    "intent_hash": job["intent_hash"],
                    "exact_content": job["request"]["content"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        (output / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        service.advance_one()
        report["no_destination_effect_before_approval"] = not (service.root / job["id"]).exists()
        assert report["no_destination_effect_before_approval"]
        if not approve_fixture:
            report["reason"] = "Review only. No StackEdit write approved."
            return report
        # The flag approves only this fixed public fixture at the displayed StackEdit destination.
        service.approve(
            job["id"],
            BrowserApproval(
                expected_version=job["version"], intent_hash=job["intent_hash"], public_only=True
            ),
            "acceptance-approve",
            session_hash=session_hash,
        )
        service.advance_one()
        result = service.detail(job["id"], review=True)
        report.update(
            state=result["state"],
            error=result["error"],
            result=result["result"],
            history=result["history"],
            cleanup_confirmed=result["cleanup_confirmed"],
        )
        if result["state"] != "succeeded":
            # No blind retry, even when the application may have completed the effect.
            report["read_only_reconcile"] = service.reconcile(job["id"], session_hash=session_hash)
            raise DomainError(result["error"] or "BROWSER_ACCEPTANCE_INCOMPLETE", 409)
        body, filename = service.export(job["id"], session_hash=session_hash)
        assert body == job["request"]["content"].encode("utf-8")
        assert hashlib.sha256(body).hexdigest() == result["result"]["sha256"]
        assert result["result"]["download_count"] == 1
        assert result["result"]["browser_close_confirmed"]
        assert result["result"]["process_cleanup_confirmed"] and result["cleanup_confirmed"]
        artifact_id = result["result"]["artifact_id"]
        assert artifact_id
        artifact, stored = runtime.artifacts.download(artifact_id, session_hash=session_hash)
        assert stored == body and artifact["origin"] == "browser_download"
        # Save a copy of the independently read actual application export, never generated text.
        with (output / filename).open("xb") as stream:
            stream.write(body)
        repeated = service.prepare(payload, "acceptance-prepare", session_hash=session_hash)["job"]
        service.advance_one()
        with runtime.store.connection() as conn:
            effects = conn.execute("SELECT COUNT(*) FROM browser_effects").fetchone()[0]
        assert repeated["id"] == job["id"] and effects == 1
        report.update(
            acceptance_passed=True,
            stackedit_live_ui_exercised=True,
            artifact_independent_readback=True,
            actual_export_file=filename,
            repeat_prepare_single_effect=True,
            actual_export_sha256=hashlib.sha256(body).hexdigest(),
            application_export_bytes=len(body),
        )
        runtime.store.logout(token)
        return report
    except Exception as exc:
        report["error"] = exc.code if isinstance(exc, DomainError) else type(exc).__name__
        if report["state"] in {"starting", "review", "succeeded"}:
            report["state"] = "blocked_or_failed"
        return report
    finally:
        if service:
            service.shutdown()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["runtime_retained_for_inspection"] = True
        (output / "evidence.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chromium",
        type=Path,
        required=True,
        help="Absolute executable from an already authorized official installation",
    )
    parser.add_argument("--output", type=Path, required=True, help="New private evidence directory")
    parser.add_argument(
        "--approve-public-fixture",
        action="store_true",
        help="Approve the fixed public/synthetic brief in StackEdit and its local export",
    )
    args = parser.parse_args()
    if not args.chromium.is_absolute():
        parser.error("--chromium must be an absolute path")
    report = run(args.chromium, args.output, args.approve_public_fixture)
    print(
        json.dumps(
            {
                "state": report["state"],
                "error": report.get("error"),
                "evidence": str(args.output / "evidence.json"),
            },
            indent=2,
        )
    )
    return (
        0
        if report["acceptance_passed"] or (report["state"] == "review" and not report.get("error"))
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
