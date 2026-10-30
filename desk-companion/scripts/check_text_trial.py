"""Offline-only synthetic text-adapter preview, isolated from inherited credentials.

No live flag, credential input, custom prompt, runtime path or dispatch option.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WALL_SECONDS = 45


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # Do not echo rejected command-line values into logs.
        self.exit(2, "Invalid offline preflight arguments; see --help.\n")


def _supervise(command, *, timeout=WALL_SECONDS):
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env={},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except OSError:
        return {"status": "offline_preflight_failed", "live_acceptance": "not_run"}, 1
    except subprocess.TimeoutExpired:
        # subprocess.run kills and reaps the worker before raising.
        return {"status": "offline_preflight_timeout", "live_acceptance": "not_run"}, 1
    if result.returncode != 0 or len(result.stdout) > 64 * 1024:
        return {"status": "offline_preflight_failed", "live_acceptance": "not_run"}, 1
    try:
        report = json.loads(result.stdout)
        if report.get("status") != "offline_preflight_passed":
            raise ValueError()
    except (ValueError, AttributeError):
        return {"status": "offline_preflight_failed", "live_acceptance": "not_run"}, 1
    report["supervision"] = {
        "worker_timeout_seconds": timeout,
        "credential_environment_inherited": False,
        "notice": "Local process timeout only; no provider cancellation or billing cap claim",
    }
    return report, 0


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--provider", required=True, choices=["qwen", "gemini"])
    parser.add_argument(
        "--model", required=True, help="Explicit preview identifier, not availability proof"
    )
    parser.add_argument(
        "--endpoint", required=True, help="Approved base endpoint; empty selects Gemini default"
    )
    parser.add_argument("--offline-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.offline_worker:
        sys.path.insert(0, str(ROOT / "backend"))
        from desk.text_trial_preflight import offline_preflight

        try:
            report = offline_preflight(
                provider=args.provider, model=args.model, endpoint=args.endpoint
            )
        except Exception:
            print('{"status":"offline_preflight_failed","live_acceptance":"not_run"}')
            return 1
        print(json.dumps(report, ensure_ascii=False))
        return 0
    command = [
        sys.executable,
        "-I",
        str(Path(__file__).resolve()),
        "--offline-worker",
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--endpoint",
        args.endpoint,
    ]
    report, code = _supervise(command)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
