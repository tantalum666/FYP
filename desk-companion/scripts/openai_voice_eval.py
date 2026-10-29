#!/usr/bin/env python3
"""Explicit short live tests, guarded by one persistent USD5 experiment ledger."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from voice_eval.budget import Budget  # noqa: E402
from voice_eval.fixtures import Fixture, LINES, speech  # noqa: E402
from voice_eval.session import Session, load_key  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--model",
        choices=["gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1"],
        required=True,
    )
    p.add_argument("--case", choices=list(LINES), required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--allow-paid", action="store_true")
    args = p.parse_args()
    if not args.allow_paid or not args.run_id.replace("-", "").isalnum():
        p.error("An explicit paid-test flag and unique alphanumeric run ID are required")
    for setting in (
        "DESK_TEXT_BACKGROUND",
        "DESK_MEMORY_EXTRACT",
        "DESK_WEB_PUSH",
        "DESK_COMPUTER_ENABLED",
        "DESK_LINUX_DESKTOP_ENABLED",
    ):
        os.environ[setting] = "0"
    os.environ["DESK_TEXT_PROVIDER"] = os.environ["DESK_VOICE_PROVIDER"] = "none"
    private = ROOT / ".runtime/openai-realtime-20261029"
    output = ROOT.parent / "output/qa/2026-10-29-openai-realtime"
    output.mkdir(parents=True, exist_ok=True)
    key = load_key(ROOT / ".env.local")
    audio = speech(args.case, private / "inputs")
    stop = speech("stop-en", private / "inputs") if args.case == "interrupt-en" else None
    fixture = Fixture(private / "fixtures" / args.run_id, args.case)
    session = Session(args.model, fixture, audio, stop, language=LINES[args.case][0])
    budget = Budget(private / "budget.sqlite3")
    reserve = (
        0.25 if args.model == "gpt-live-1" else 1.5 if args.model == "gpt-realtime-2.1" else 0.5
    )
    budget.reserve(args.run_id, args.model, reserve)
    result = asyncio.run(session.run(key))
    result.update(
        case=args.case,
        run_id=args.run_id,
        reserved_usd=reserve,
        synthetic_input=LINES[args.case][1],
    )
    budget.finish(
        args.run_id,
        estimate=result["estimated_uncached_usd"],
        finalized=result["usage_finalized"],
        result={"end_reason": result["end_reason"], "errors": result["errors"]},
    )
    (output / (args.run_id + ".json")).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
    session.save_audio(output / (args.run_id + ".wav"))
    (output / "budget.json").write_text(json.dumps(budget.snapshot(), indent=2) + "\n")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "run_id",
                    "model",
                    "ready",
                    "end_reason",
                    "errors",
                    "transcript",
                    "estimated_uncached_usd",
                    "usage_finalized",
                )
            },
            ensure_ascii=False,
        )
    )
    print(json.dumps({k: v for k, v in budget.snapshot().items() if k != "runs"}))


if __name__ == "__main__":
    main()
