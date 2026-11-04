#!/usr/bin/env python3
"""Offline, receipt-driven planner exercising real Work -> Chromium/Calc/Writer/PDF.

No model/API request. Requires the existing isolated application desktop. The
owner steering/answer are explicit synthetic test events, not inferred consent.
Phase run exits 73 after a real save with a deliberately lost completion reply.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.agent_run_schemas import AgentDecision, RunAction, RunCreate, RunToolCall
from desk.app import create_app
from desk.permissions import PermissionChange
from desk.personal_context import ContextSettings
from desk.tasks import TaskInput
from desk.text_ai import TextConfig

SOURCE = "work-continuation/quotes.html"
QUOTE_HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Fictional print quotations</title>
<h1>Fictional quotations for Group 2 workflow testing</h1><p>Amounts in HKD. Day 3 is Wednesday; day 4 Thursday. Shipping is per order. Reserve 10%.</p>
<pre>DATA_BEGIN
vendor,unit,minimum,shipping,day
Aster,18.50,30,40,3
Birch,16.00,50,20,3
Cedar,19.00,36,0,4
DATA_END</pre><p>These are fictional quotes, not offers. No purchase or contact is authorized.</p></html>"""


def cell(address, value, *, kind=None):
    return {
        "cell": address,
        "kind": kind
        or (
            "number"
            if isinstance(value, (int, float))
            else "formula"
            if value.startswith("=")
            else "text"
        ),
        "value": value,
    }


def workbook(goal, vendors, base=None):
    quantity, budget = [int(x) for x in re.search(r"quantity=(\d+).*budget=(\d+)", goal).groups()]
    cells = [
        cell("A1", "Requested quantity"),
        cell("B1", quantity),
        cell("A2", "Budget HKD"),
        cell("B2", budget),
        cell("A3", "Reserve"),
        cell("B3", 0.1),
        cell("A4", "Deadline day"),
        cell("B4", 3),
    ]
    for col, label in zip(
        "ABCDEFGHI",
        [
            "Vendor",
            "Unit HKD",
            "Minimum",
            "Shipping",
            "Ready day",
            "Order qty",
            "Subtotal",
            "With reserve",
            "Feasible",
        ],
    ):
        cells.append(cell(col + "6", label))
    for row, quote in enumerate(vendors, 7):
        for col, value in zip(
            "ABCDE",
            [
                quote["vendor"],
                float(quote["unit"]),
                int(quote["minimum"]),
                float(quote["shipping"]),
                int(quote["day"]),
            ],
        ):
            cells.append(cell(col + str(row), value))
        cells.extend(
            [
                cell(f"F{row}", f"=MAX($B$1,C{row})"),
                cell(f"G{row}", f"=F{row}*B{row}+D{row}"),
                cell(f"H{row}", f"=ROUND(G{row}*(1+$B$3),2)"),
                cell(f"I{row}", f"=IF(AND(E{row}<=$B$4,H{row}<=$B$2),1,0)"),
            ]
        )
    return {
        "kind": "workbook",
        "filename": "comparison.xlsx",
        "source_job_id": base,
        "sheets": [{"sheet": "Quotes", "cells": cells}],
    }


class QuotePlanner:
    """Deterministic fixture decisions use only the supplied Work context/results."""

    def __init__(self):
        self.context_sizes = []

    def __call__(self, system, ctx, schema, purpose):
        if purpose != "agent_run_decision":
            raise RuntimeError("This QA server only accepts the offline Work fixture")
        self.context_sizes.append(len(json.dumps(ctx, ensure_ascii=False).encode()))
        if not ctx["plan"]:
            return AgentDecision(
                action="plan",
                plan=[
                    "Read selected quote and task",
                    "Calculate feasible suppliers in Calc",
                    "Resolve quantity choice",
                    "Write decision and export PDF",
                    "Verify every output",
                ],
            )
        task = next((e for e in ctx["observations"] if e["kind"] == "task"), None)
        if not task:
            selected = next(e for e in ctx["available_evidence"] if e["kind"] == "task")
            return AgentDecision(action="read", evidence_id=selected["id"])
        quote = next((e for e in ctx["observations"] if e["kind"] == "application"), None)
        if not quote:
            return AgentDecision(
                action="tool",
                tool_call=RunToolCall(
                    tool="application_source_read", arguments={"source_id": SOURCE}
                ),
            )
        text = quote["excerpt"].split("DATA_BEGIN", 1)[1].split("DATA_END", 1)[0].strip()
        vendors = list(csv.DictReader(io.StringIO(text)))
        effects = [e for e in ctx["reviewed_effects"] if e.get("tool") == "application_job_draft"]
        if any(e["state"] != "verified" for e in effects):
            return AgentDecision(
                action="ask",
                question="An earlier application result is not verified. Inspect that result before another write.",
            )
        revised = "quantity=48" in ctx["goal"]
        wanted = 2 if revised else 1
        books = [e for e in effects if e.get("filename") == "comparison.xlsx"]
        if len(books) < wanted:
            return self.job(
                task,
                quote,
                "revised_budget" if books else "initial_budget",
                workbook(ctx["goal"], vendors, books[-1]["reference_id"] if books else None),
            )
        if revised and not ctx["answers"]:
            return AgentDecision(
                action="ask",
                question="Birch's minimum order is 50 for the requested 48. Accept two extra copies within the HKD 950 budget?",
            )
        book = books[-1]
        result = next(
            r["result"] for r in ctx["tool_results"] if r["reference_id"] == book["reference_id"]
        )
        values = {
            c["cell"]: c.get("value", c.get("text"))
            for c in result["readback"]["sheets"][0]["cells"]
        }
        feasible = [row for row in range(7, 10) if values[f"I{row}"] == 1]
        chosen = min(feasible, key=lambda row: values[f"H{row}"])
        docs = [e for e in effects if e.get("filename") == "decision.odt"]
        if not docs:
            blocks = [
                {"kind": "title", "text": "Group 2 · Print decision"},
                {
                    "kind": "paragraph",
                    "text": "Fictional workflow acceptance. Decisions were scripted offline; applications and file verification are real. No purchase was made.",
                },
                {"kind": "heading", "text": "Current requirements"},
                {"kind": "paragraph", "text": ctx["goal"]},
                {
                    "kind": "paragraph",
                    "text": "Owner test answer: "
                    + (
                        ctx["answers"][-1]
                        if ctx["answers"]
                        else "No extra-quantity choice required."
                    ),
                },
                {
                    "kind": "table",
                    "rows": [["Vendor", "Order", "Total with reserve", "Feasible"]]
                    + [
                        [
                            str(values[f"A{r}"]),
                            str(int(values[f"F{r}"])),
                            f"HKD {values[f'H{r}']:.2f}",
                            "Yes" if values[f"I{r}"] == 1 else "No",
                        ]
                        for r in range(7, 10)
                    ],
                },
                {
                    "kind": "paragraph",
                    "text": f"Selected: {values[f'A{chosen}']}; {int(values[f'F{chosen}'])} copies; HKD {values[f'H{chosen}']:.2f} including shipping and 10% reserve.",
                },
                {"kind": "page_break"},
                {"kind": "heading", "text": "Verification and remaining actions"},
                {
                    "kind": "paragraph",
                    "text": "Calc formulas were recalculated and the saved workbook reopened. This document uses those returned cell values. PDF export is a separate dependent job. Check supplier availability again before any real order.",
                },
                {
                    "kind": "paragraph",
                    "text": "Previous workbook versions remain downloadable. A lost save receipt must be reconciled without repeating the write. Paid model quality and real purchasing are outside this acceptance.",
                },
            ]
            return self.job(
                task,
                quote,
                "decision_note",
                {"kind": "document", "filename": "decision.odt", "blocks": blocks},
                [book["reference_id"]],
            )
        if not any(e.get("filename") == "decision.pdf" for e in effects):
            return self.job(
                task,
                quote,
                "decision_pdf",
                {
                    "kind": "pdf",
                    "filename": "decision.pdf",
                    "source_job_id": docs[-1]["reference_id"],
                },
                [book["reference_id"]],
            )
        if not ctx["artifacts"]:
            return AgentDecision(
                action="report",
                report={
                    "summary": "Real application outputs verified under an offline scripted planner; no purchase and no live-model result.",
                    "sections": [
                        {
                            "title": "Decision and evidence",
                            "text": f"Selected {values[f'A{chosen}']} at HKD {values[f'H{chosen}']:.2f}. Original and revised workbook, Writer document and PDF are linked to this Work. File checks do not independently prove semantic model quality.",
                            "evidence_ids": [e["id"] for e in ctx["observations"]],
                        }
                    ],
                },
            )
        return AgentDecision(action="finish")

    @staticmethod
    def job(task, quote, stage, step, dependencies=None):
        return AgentDecision(
            action="tool",
            tool_call=RunToolCall(
                tool="application_job_draft",
                arguments={
                    "title": stage.replace("_", " ").title(),
                    "task_id": task["record_id"],
                    "task_version": task["version"],
                    "stage": stage,
                    "sources": [{"source_id": SOURCE, "sha256": quote["sha256"]}],
                    "depends_on": dependencies or [],
                    "step": step,
                },
            ),
        )


def configure(directory, *, scheduler=False):
    app = create_app(directory, password="fictional-work-acceptance", scheduler=scheduler)
    r = app.state.runtime
    r.text_ai.config = TextConfig(
        provider="gemini", model="offline-scripted-no-network", api_key="fixture-no-network"
    )
    planner = QuotePlanner()
    r.text_ai.generate = planner
    settings = r.personal_context.settings()
    dest = next(d["id"] for d in settings["destinations"] if d["kind"] == "text")
    if dest not in settings["approved_destinations"]:
        r.personal_context.update(
            ContextSettings(
                expected_version=settings["version"],
                save_text_history=False,
                use_text_history_in_ai=False,
                use_memory_in_ai=False,
                share_business_context=True,
                approved_destinations=[dest],
            ),
            "qa-context",
        )
    return app, r, planner, dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--phase", choices=["run", "resume", "review", "serve"], required=True)
    parser.add_argument("--run-real-apps", action="store_true")
    parser.add_argument("--port", type=int, default=8861)
    args = parser.parse_args()
    if not args.run_real_apps:
        parser.error("Explicit --run-real-apps required")
    args.runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.report.mkdir(parents=True, exist_ok=True)
    app, r, planner, dest = configure(args.runtime, scheduler=args.phase == "serve")
    if args.phase == "serve":
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=args.port)
        return
    owner = {"kind": "owner", "session": r.store.create_owner_session()}
    control = args.runtime / "acceptance.json"
    state = json.loads(control.read_text()) if control.exists() else {}

    def save():
        control.write_text(json.dumps(state, indent=2))
        control.chmod(0o600)

    def detail():
        return r.agent_runs.detail(state["run_id"], owner)

    def act(name, **extra):
        run = detail()["run"]
        return r.agent_runs.action(
            run["id"],
            RunAction(action=name, expected_version=run["version"], **extra),
            f"qa/{name}/{run['version']}",
            owner,
        )

    if args.phase in {"run", "review"}:
        if state:
            raise SystemExit(
                "Use a fresh core directory for a new acceptance; existing run retained"
            )
        path = r.jobs.applications.sources.root / SOURCE
        path.parent.mkdir(exist_ok=True, mode=0o700)
        if path.exists() and path.read_text() != QUOTE_HTML:
            raise SystemExit("Existing fixture differs; not overwritten")
        path.write_text(QUOTE_HTML)
        task = r.tasks.create(
            TaskInput(
                title="QA · Offline planner / real print applications", follow_up_enabled=False
            ),
            "qa-task",
        )["task"]
        if args.phase == "run":
            policy = r.permissions.snapshot()
            r.permissions.change(
                PermissionChange(mode="full", expected_version=policy["version"]), "qa-full"
            )
        run = r.agent_runs.create(
            RunCreate(
                goal="Compare fictional suppliers; quantity=36 budget=900 deadline=Wednesday. Prepare a spreadsheet, decision document and PDF.",
                mode="model",
                retain=True,
                task_ids=[task["id"]],
                scope_revision=r.agent_runs.scope(owner)["scope_revision"],
                provider_destination_id=dest,
                share_sources_with_provider=True,
                allow_application_jobs=True,
                application_source_ids=[SOURCE],
                model_call_budget=20,
                tool_call_budget=12,
            ),
            "qa-work",
            owner,
        )["run"]
        state.update(run_id=run["id"], task_id=task["id"], steered=False, events=[])
        save()
    if args.phase == "run":
        original = r.jobs.applications.execute

        def lose_reply(request, checkpoint):
            original(request, checkpoint)
            if request["stage"] == "revised_budget":
                path = r.jobs.applications.target(request)
                state["lost_reply"] = {
                    "job_id": request["artifact_id"],
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mtime_ns": path.stat().st_mtime_ns,
                }
                save()
                raise RuntimeError("Deliberately lost executor completion after actual publication")

        r.jobs.applications.execute = lose_reply
    for _ in range(200):
        r.agent_runs.advance_one()
        d = detail()
        run = d["run"]
        if args.phase == "review" and run["state"] == "waiting_review":
            print(
                json.dumps(
                    {
                        "run_id": run["id"],
                        "state": run["state"],
                        "application_jobs": len(d["application_jobs"]),
                    }
                )
            )
            return
        r.jobs.run_one()
        if args.phase == "run" and state.get("lost_reply"):
            state["events"].append("saved_then_completion_lost")
            save()
            print(json.dumps({"checkpoint": "saved_before_ack", **state["lost_reply"]}), flush=True)
            raise SystemExit(73)
        verified = [e for e in run.get("effects", []) if e.get("state") == "verified"]
        if len(verified) == 1 and not state["steered"]:
            act(
                "steer",
                goal="Revised request: quantity=48 budget=950 deadline=Wednesday. Keep prior versions, ask about minimum-order extras, revise spreadsheet and prepare a decision document plus PDF.",
            )
            state["steered"] = True
            state["events"].append("synthetic_owner_goal_changed")
            save()
        elif run["state"] == "waiting_input":
            if "minimum order" not in (run.get("question") or ""):
                raise RuntimeError(run.get("question"))
            act(
                "answer",
                answer="Synthetic owner answer: accept 50 copies (two extra), within the HKD 950 budget.",
            )
            state["events"].append("synthetic_owner_answered")
            save()
        elif run["state"] in {"succeeded", "partial", "blocked", "failed"}:
            (args.report / "run-result.json").write_text(json.dumps(d, indent=2))
            if run["state"] != "succeeded":
                raise RuntimeError(f"{run['state']}: {run['state_reason']}")
            jobs = d["application_jobs"]
            lost = next(j for j in jobs if j["id"] == state["lost_reply"]["job_id"])
            path = r.jobs.applications.target(lost["request"])
            unchanged = (
                hashlib.sha256(path.read_bytes()).hexdigest() == state["lost_reply"]["sha256"]
                and path.stat().st_mtime_ns == state["lost_reply"]["mtime_ns"]
            )
            assert unchanged, "Recovery rewrote the saved workbook"
            cells = {c["cell"]: c for c in lost["result"]["readback"]["sheets"][0]["cells"]}
            assert [cells[f"H{n}"]["value"] for n in (7, 8, 9)] == [1020.8, 902.0, 1003.2]
            assert [cells[f"I{n}"]["value"] for n in (7, 8, 9)] == [0.0, 1.0, 0.0]
            outputs = []
            for index, job in enumerate(jobs):
                filename, body = r.jobs.application_download(job["id"])
                target = args.report / f"{index + 1}-{filename}"
                target.write_bytes(body)
                outputs.append(
                    {
                        "job_id": job["id"],
                        "filename": target.name,
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body),
                        "apps": job["result"]["apps_verified"],
                    }
                )
            receipt = {
                "state": run["state"],
                "planner": "offline_scripted_receipt_driven",
                "paid_model_calls": 0,
                "real_application_jobs": len(jobs),
                "events": state["events"],
                "recovery_hash_and_mtime_unchanged": unchanged,
                "max_model_context_bytes": max(planner.context_sizes),
                "outputs": outputs,
                "quality": "not_live_model_acceptance",
            }
            (args.report / "verification.json").write_text(json.dumps(receipt, indent=2))
            print(json.dumps(receipt))
            return
        time.sleep(0.1)
    raise RuntimeError("Bounded acceptance did not reach a terminal state")


if __name__ == "__main__":
    main()
