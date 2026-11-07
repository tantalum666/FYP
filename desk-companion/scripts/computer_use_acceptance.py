#!/usr/bin/env python3
"""Real browser + native computer wire rehearsal, with zero inference requests.

Uses scripted fixture decisions through MockTransport; clicks/typing/screenshots
go through the production worker and existing JobService. No login or transaction.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.app import create_app
from desk.computer_use_models import ComputerUseInput
from desk.computer_use_protocol import OpenAIComputerProtocol
from desk.jobs import JobApproval
from desk.text_ai import TextConfig


class RehearsalProtocol(OpenAIComputerProtocol):
    def __init__(self, config, goal, origins, **kwargs):
        super().__init__(config, goal, origins, **kwargs)
        self.phase, self.goal = 0, goal
        self.observation = None
        self.transport = httpx.MockTransport(self.respond)

    def control(self, label):
        items = [
            item for item in self.observation["controls"] if label.lower() in item["label"].lower()
        ]
        if not items:
            raise LookupError(label)
        return items[0]

    def click(self, label):
        item = self.control(label)
        return {"type": "click", "x": item["x"], "y": item["y"], "button": "left"}

    def fill(self, label, text):
        return [
            self.click(label),
            {
                "type": "keypress",
                "keys": ["META" if self.observation.get("platform") == "darwin" else "CTRL", "A"],
            },
            {"type": "type", "text": text},
        ]

    def actions(self):
        if self.goal.startswith("initial cart"):
            if self.phase == 0:
                return self.fill("Quantity", "3") + [
                    self.click("Add to cart"),
                    self.click("Open cart"),
                ]
            return None
        if self.goal.startswith("revise cart"):
            if self.phase == 0:
                return [self.click("Open cart")]
            if self.phase == 1:
                return [self.click("Refresh price")]
            if self.phase == 2:
                return (
                    self.fill("Quantity", "4")
                    + [self.click("Add to cart")]
                    + self.fill("Discount code", "SAVE10")
                    + [self.click("Apply code")]
                )
            return [self.click("Place order")]
        if self.goal.startswith("flight"):
            if self.phase == 0:
                return (
                    self.fill("Departure date", "2026-11-22")
                    + self.fill("Adults", "2")
                    + [
                        self.click("Baggage"),
                        {"type": "keypress", "keys": ["END"]},
                        {"type": "keypress", "keys": ["ARROWUP"]},
                        {"type": "keypress", "keys": ["ENTER"]},
                        self.click("Search flights"),
                    ]
                )
            if self.phase == 1:
                return [self.click("View Pearl fare")]
            return [self.click("Confirm booking")]
        if self.goal.startswith("public"):
            return [self.click("Travel")] if self.phase == 0 else None
        raise ValueError("Unknown rehearsal")

    def respond(self, request):
        body = json.loads(request.content)
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert body["tools"] == [{"type": "computer"}] and body["store"] is False
        try:
            actions = self.actions()
            self.phase += 1
        except LookupError:
            actions = [{"type": "scroll", "x": 1100, "y": 700, "scroll_x": 0, "scroll_y": 500}]
        if actions is None:
            output = [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Review the observed page; no order or booking was made.",
                        }
                    ],
                }
            ]
        else:
            output = [
                {
                    "type": "computer_call",
                    "call_id": f"fixture-{self.observation['sequence']}",
                    "status": "completed",
                    "actions": actions,
                }
            ]
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": output,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        )

    def step(self, observation, screenshot, checkpoint):
        self.observation = observation
        assert screenshot[:8] == b"\x89PNG\r\n\x1a\n"
        return super().step(observation, screenshot, checkpoint)


def execute(runtime, principal, key, goal, url, *, source=None, expected_state="succeeded"):
    job = runtime.jobs.prepare(
        ComputerUseInput(
            title=goal,
            goal=goal,
            start_url=url,
            public_only=True,
            share_screen=True,
            max_steps=10,
            source_job_id=source,
        ),
        key,
        principal=principal,
    )["job"]
    review = runtime.jobs.detail(job["id"], review=True)
    assert review["state"] == "review"
    runtime.jobs.approve(
        job["id"],
        JobApproval(expected_version=review["version"], intent_hash=review["intent_hash"]),
        key + "/approve",
    )
    runtime.jobs.run_one()
    result = runtime.jobs.detail(job["id"], review=True)
    if result["state"] != expected_state:
        raise RuntimeError(f"{result['state']}: {result['error']}; job {job['id']}")
    assert result["result"]["quality"] == "not_goal_completion"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-real-browser", action="store_true")
    parser.add_argument("--case", choices=["shopping", "flights", "public", "stop"], required=True)
    parser.add_argument("--chromium", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--browser-proxy", default="")
    args = parser.parse_args()
    if not args.run_real_browser or args.runtime.exists():
        parser.error("Explicit real-browser flag and a fresh runtime required")
    os.environ.update(
        DESK_BROWSER_EXECUTABLE=str(args.chromium),
        DESK_COMPUTER_USE_ENABLED="1",
        DESK_BROWSER_PROXY_URL=args.browser_proxy,
        DESK_TEXT_PROVIDER="none",
        DESK_VOICE_PROVIDER="none",
        DESK_TEXT_BACKGROUND="0",
        DESK_MEMORY_EXTRACT="0",
        DESK_WEB_PUSH="0",
    )
    args.report.mkdir(parents=True, exist_ok=True)
    app = create_app(args.runtime, password="fictional-computer-acceptance", scheduler=False)
    runtime = app.state.runtime
    runtime.text_ai.config = TextConfig(
        "openai", "gpt-6.1-sol", "https://api.openai.com/v1/responses", "fixture-no-network"
    )
    runtime.jobs.computer_use.protocol_factory = RehearsalProtocol
    if args.case == "stop":

        def stopping_protocol(config, goal, origins, **kwargs):
            protocol = RehearsalProtocol(
                config, "initial cart" if goal.startswith("stop") else goal, origins, **kwargs
            )
            step = protocol.step

            def observed(observation, screenshot, checkpoint):
                if goal.startswith("stop") and observation["sequence"] == 2:
                    with runtime.store.connection() as conn:
                        active = conn.execute(
                            "SELECT id FROM computer_jobs WHERE state='running'"
                        ).fetchone()[0]
                    runtime.jobs.cancel(active, "synthetic-owner-stop")
                return step(observation, screenshot, checkpoint)

            protocol.step = observed
            return protocol

        runtime.jobs.computer_use.protocol_factory = stopping_protocol
    principal = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
    jobs = []
    if args.case == "stop":
        stopped = execute(
            runtime,
            principal,
            "stopped",
            "stop after cart preparation",
            "demo:shopping",
            expected_state="cancelled",
        )
        jobs.append(stopped)
        assert stopped["result"]["readback"]["reason"] == "stopped_by_owner"
        assert not runtime.jobs.computer_use.blocker.exists()
        final = execute(
            runtime,
            principal,
            "after-stop",
            "revise cart after explicit stop",
            "demo:shopping",
            source=stopped["id"],
        )
        jobs.append(final)
        assert "Total: HKD 55.80" in final["result"]["readback"]["observation"]["text"]
    elif args.case == "shopping":
        initial = execute(
            runtime, principal, "cart-first", "initial cart: 3 packs within HKD60", "demo:shopping"
        )
        jobs.append(initial)
        assert "Total: HKD 43.50" in initial["result"]["readback"]["observation"]["text"]
        final = execute(
            runtime,
            principal,
            "cart-revised",
            "revise cart: new price, 4 packs, SAVE10; review final total",
            "demo:shopping",
            source=initial["id"],
        )
        jobs.append(final)
        text = final["result"]["readback"]["observation"]["text"]
        assert "Total: HKD 55.80" in text and "Quantity: 4 packs" in text
    elif args.case == "flights":
        final = execute(
            runtime,
            principal,
            "flight",
            "flight: HKG to TYO, 22 Nov, 2 adults, 20 kg, all fees within HKD2200",
            "demo:flights",
        )
        jobs.append(final)
        text = final["result"]["readback"]["observation"]["text"]
        assert all(
            item in text
            for item in [
                "HKD 2080.00",
                "2026-11-23 00:15 Asia/Tokyo",
                "Baggage: 20 kg",
                "Adults: 2",
            ]
        ), text
    else:
        final = execute(
            runtime,
            principal,
            "public",
            "public catalogue: open Travel category",
            "https://books.toscrape.com/",
        )
        jobs.append(final)
        assert "/travel_2/" in final["result"]["readback"]["observation"]["url"]
    if args.case != "public":
        assert final["result"]["outcome"] == "needs_owner"
        assert final["result"]["readback"]["reason"] == "final_submission_needs_owner"
        assert final["result"]["readback"]["demo_submissions"] == 0
    outputs = []
    for index, job in enumerate(jobs):
        receipt = job["result"]["readback"]
        folder = runtime.jobs.computer_use.root / job["id"]
        screen = folder / receipt["observation"]["screen"]
        target = args.report / f"{index + 1}-screen.png"
        shutil.copyfile(screen, target)
        outputs.append(
            {
                "id": job["id"],
                "outcome": job["result"]["outcome"],
                "reason": receipt["reason"],
                "observation": receipt["observation"],
                "state_sha256": receipt["state_sha256"],
                "screen": target.name,
                "screen_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "browser_version": receipt["browser_version"],
            }
        )
    result = {
        "case": args.case,
        "planner": "scripted_mock_responses_native_computer_calls",
        "real_browser": True,
        "paid_model_requests": 0,
        "real_orders_or_bookings": 0,
        "cleanup_confirmed": not runtime.jobs.computer_use.blocker.exists(),
        "outputs": outputs,
    }
    (args.report / "verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "outputs"}))


if __name__ == "__main__":
    main()
