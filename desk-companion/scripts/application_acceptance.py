#!/usr/bin/env python3
"""Explicit scripted execution-layer acceptance; not a voice/agent benchmark.

Uses the same granular services exposed to a future model, reads the connected
sources, and lets actual Calc formulas determine costs. No reference solver or
controller answer file is imported. Run phases in separate processes; revise
deliberately exits73 after publishing the final workbook but before acknowledging
the job. Recover must reconcile its original receipt without executing it again.
"""

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from desk.app import create_app  # noqa: E402
from desk.application_models import ApplicationJobInput  # noqa: E402
from desk.permissions import PermissionChange  # noqa: E402
from desk.schemas import CreateEvents, EventAction, EventInput  # noqa: E402
from desk.tasks import TaskAction, TaskInput  # noqa: E402


def cell(address, value, kind=None, fmt="plain"):
    return {
        "cell": address,
        "value": value,
        "kind": kind or ("number" if isinstance(value, (int, float)) else "text"),
        "format": fmt,
    }


def table(sheet, values):
    return {
        "sheet": sheet,
        "cells": [
            cell(chr(65 + c) + str(r + 1), value, fmt="heading" if r == 0 else "plain")
            for r, row in enumerate(values)
            for c, value in enumerate(row)
        ],
    }


def grid(snapshot, name):
    return {c["cell"]: c for s in snapshot["sheets"] if s["sheet"] == name for c in s["cells"]}


class Controller:
    def __init__(self, directory, report, attempt=1):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "acceptance-controller.json"
        self.report = report
        self.attempt = attempt
        report.mkdir(parents=True, exist_ok=True)
        self.state = (
            json.loads(self.path.read_text()) if self.path.exists() else {"jobs": {}, "phases": []}
        )
        self.runtime = create_app(
            directory, password="fictional-application-acceptance", scheduler=False
        ).state.runtime
        self.principal = {"kind": "owner", "session": self.runtime.store.create_owner_session()}

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2))
        temporary.chmod(0o600)
        temporary.replace(self.path)

    def task(self):
        return self.runtime.tasks.detail(self.state["task_id"])["task"]

    def update_task(self, *, next_step, status="in_progress", waiting_for=""):
        current = self.task()
        data = {key: current[key] for key in TaskInput.model_fields}
        data.update(next_step=next_step, status=status, waiting_for=waiting_for)
        self.runtime.tasks.action(
            current["id"],
            TaskAction(
                action="update",
                expected_version=current["version"],
                task=TaskInput.model_validate(data),
            ),
            f"acceptance/task-{current['version']}",
        )

    def step(self, stage, step, label, *, depends_on=None, crash=False):
        current = self.task()
        grant = self.runtime.permissions.capture(self.principal, current["id"])
        payload = ApplicationJobInput(
            title=label,
            task_id=current["id"],
            task_version=current["version"],
            stage=stage,
            step=step,
            depends_on=depends_on or [],
            sources=self.state.get("source_refs", []),
        )
        if stage in self.state["jobs"]:
            prior = self.runtime.jobs.detail(self.state["jobs"][stage], review=True)
            fields = ("task_id", "task_version", "stage", "step", "depends_on", "sources")
            public = payload.model_dump(mode="json")
            if prior["state"] == "succeeded" and all(
                prior["request"][k] == public[k] for k in fields
            ):
                if not self.runtime.jobs.application_readback(prior["id"])["result"]["verified"]:
                    raise RuntimeError("Previously completed step no longer matches its artifact")
                print(json.dumps({"stage": stage, "reused_verified_job": prior["id"]}), flush=True)
                return prior
        key = (
            "acceptance/"
            + stage
            + "/"
            + str(len(self.state["phases"]))
            + "/attempt-"
            + str(self.attempt)
        )
        reply = self.runtime.jobs.prepare(payload, key)
        job_id = reply["job"]["id"]
        self.state["jobs"][stage] = job_id
        self.save()
        self.runtime.permissions.apply_reply(reply, grant)
        if self.runtime.jobs.detail(job_id)["state"] != "queued":
            raise RuntimeError("An explicit owner decision is required before this step")
        if crash:
            original = self.runtime.jobs.applications.execute

            def lose_process(request, checkpoint):
                original(request, checkpoint)
                path = self.runtime.jobs.applications.target(request)
                self.state["lost_result"] = {
                    "job_id": job_id,
                    "pid": os.getpid(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "mtime_ns": path.stat().st_mtime_ns,
                }
                self.save()
                print(
                    json.dumps({"checkpoint": "published_before_ack", **self.state["lost_result"]}),
                    flush=True,
                )
                os._exit(73)

            self.runtime.jobs.applications.execute = lose_process
        self.runtime.jobs.run_one()
        job = self.runtime.jobs.detail(job_id, review=True)
        (
            self.report
            / (stage + "-" + str(len(self.state["phases"])) + "-" + job_id[:8] + ".json")
        ).write_text(json.dumps(job, indent=2) + "\n")
        print(
            json.dumps(
                {"stage": stage, "state": job["state"], "error": job["error"], "id": job_id}
            ),
            flush=True,
        )
        if job["state"] != "succeeded":
            raise RuntimeError("Application step did not succeed: " + str(job["error"]))
        return job

    def read_sources(self):
        service = self.runtime.jobs.applications.sources
        observations = [service.content(item["source_id"]) for item in service.listing()["sources"]]
        self.state["source_refs"] = [
            {"source_id": o["source_id"], "sha256": o["sha256"]} for o in observations
        ]
        self.state["source_observations"] = observations
        self.save()
        (self.report / "source-observations.json").write_text(
            json.dumps(observations, indent=2) + "\n"
        )
        return observations

    def data(self):
        sources = {o["source_id"]: o["observation"] for o in self.state["source_observations"]}

        def csv_rows(name):
            return list(csv.DictReader(io.StringIO(sources[name]["text"])))

        quotes = {}
        for name, source in sources.items():
            if not name.endswith(".html") or not source.get("tables"):
                continue
            quote = dict(source["tables"][0])
            old = quotes.get(quote["supplier"])
            if old is None or (quote["updated"], int(quote["revision"])) > (
                old["updated"],
                int(old["revision"]),
            ):
                quotes[quote["supplier"]] = quote
        tasks = {}
        for row in csv_rows("tasks.csv"):
            if row["id"] not in tasks or row["updated_at"] > tasks[row["id"]]["updated_at"]:
                tasks[row["id"]] = row
        # Explicit scripted interpretation of the supplied meeting update. This
        # controller is not an NLP evaluator and is never a model capability.
        if (
            "T04 Recovery boundary checks completed at14:00"
            not in sources["meeting-notes.md"]["text"]
        ):
            raise ValueError("Fixture meeting update changed; review the scripted case")
        tasks["T04"].update(status="completed", remaining_hours="0")
        return (
            quotes,
            tasks,
            {r["currency"]: float(r["HKD_per_unit"]) for r in csv_rows("fx-rates.csv")},
            csv_rows("availability.csv"),
            csv_rows("existing-events.csv"),
        )

    def slots(self, exclude_wednesday=False):
        _, _, _, availability, busy = self.data()
        spans = [
            (r["member"], datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"]))
            for r in availability
        ]
        conflicts = [
            (datetime.fromisoformat(r["start"]), datetime.fromisoformat(r["end"])) for r in busy
        ]
        slots = []
        for date in sorted({a.date() for _, a, _ in spans}):
            if exclude_wednesday and date.weekday() == 2:
                continue
            for minute in range(14 * 60, 17 * 60, 15):
                start = datetime.combine(
                    date, datetime.min.time(), tzinfo=spans[0][1].tzinfo
                ) + timedelta(minutes=minute)
                end = start + timedelta(minutes=45)
                if all(
                    any(who == member and a <= start and end <= b for who, a, b in spans)
                    for member in {x[0] for x in spans}
                ) and not any(start < b and a < end for a, b in conflicts):
                    slots.append({"start": start.isoformat(), "end": end.isoformat()})
                    break
            if len(slots) == 2:
                return slots
        raise ValueError("No two rehearsal slots")

    def workbook(self):
        quotes, tasks, fx, _, _ = self.data()
        summary = table(
            "Summary",
            [
                ["Group 2 demo budget", "Fictional execution QA"],
                ["Setting", "Value"],
                ["Budget HKD", 1300],
                ["Booklets required", 25],
                ["Print mode", "colour"],
                ["Posters", 2],
                ["Badges", 3],
                ["Reserve rate", 0.1],
                ["Latest delivery", "2026-11-05"],
                ["Quote date", "2026-10-30"],
            ],
        )
        headers = [
            "Supplier",
            "Currency",
            "Poster",
            "Colour",
            "B/W",
            "Badge",
            "Delivery fee",
            "Discount",
            "Minimum",
            "HKD/unit",
            "Delivery",
            "Valid until",
            "Quote",
            "Bought",
            "Items",
            "Delivered",
            "HKD",
            "Reserve",
            "Total",
            "Eligible",
        ]
        sheet = table("Quotes", [headers])
        for index, supplier in enumerate(sorted(quotes), 2):
            q = quotes[supplier]
            values = [
                supplier,
                q["currency"],
                *[
                    float(q[k])
                    for k in (
                        "poster",
                        "colour",
                        "black_white",
                        "badge",
                        "delivery_fee",
                        "item_discount",
                    )
                ],
                int(q["min_booklets"]),
                fx[q["currency"]],
                q["delivery"],
                q["valid_until"],
                q["id"],
            ]
            sheet["cells"].extend(
                cell(chr(65 + c) + str(index), value) for c, value in enumerate(values)
            )
            formulas = {
                "N": f"=MAX(Summary.B4;I{index})",
                "O": f'=Summary.B6*C{index}+N{index}*IF(Summary.B5="colour";D{index};E{index})+Summary.B7*F{index}',
                "P": f"=ROUND(O{index}*(1-H{index})+G{index};2)",
                "Q": f"=ROUND(P{index}*J{index};2)",
                "R": f"=ROUND(Q{index}*Summary.B8;2)",
                "S": f"=Q{index}+R{index}",
                "T": f'=IF(AND(K{index}<=Summary.B9;L{index}>=Summary.B10;S{index}<=Summary.B3);"eligible";"excluded")',
            }
            sheet["cells"].extend(
                cell(
                    c + str(index), value, "formula", "money" if c in "P Q R S".split() else "plain"
                )
                for c, value in formulas.items()
            )
            row = index + 9
            summary["cells"].extend(
                [
                    cell(f"A{row}", supplier),
                    cell(f"B{row}", f"=Quotes.S{index}", "formula", "money"),
                    cell(f"C{row}", f"=Quotes.T{index}", "formula"),
                    cell(f"D{row}", f'=IF(C{row}="eligible";B{row};1000000)', "formula"),
                    cell(f"E{row}", f"=Quotes.N{index}-Summary.B4", "formula"),
                ]
            )
        summary["cells"].extend(
            [
                cell("A16", "Lowest feasible total"),
                cell("B16", "=MIN(D11:D14)", "formula", "money"),
                cell("A17", "Plan status"),
                cell("B17", '=IF(B16=1000000;"Clarification needed";"Feasible")', "formula"),
                cell("A18", "Selected supplier"),
                cell(
                    "B18",
                    '=IF(B16=1000000;"No valid option";IF(D11=B16;A11;IF(D12=B16;A12;IF(D13=B16;A13;A14))))',
                    "formula",
                ),
                cell("A19", "Extra booklets"),
                cell(
                    "B19",
                    "=IF(B16=1000000;0;IF(D11=B16;E11;IF(D12=B16;E12;IF(D13=B16;E13;E14))))",
                    "formula",
                ),
            ]
        )
        task_rows = [["Task", "Work", "Owner", "Status", "Hours", "Dependencies", "Updated"]]
        task_rows.extend(
            [
                t["id"],
                t["title"],
                t["owner"],
                t["status"],
                float(t["remaining_hours"]),
                t["depends_on"],
                t["updated_at"],
            ]
            for t in tasks.values()
        )
        tasks_sheet = table("TaskPlan", task_rows)
        tasks_sheet["cells"].extend(
            [cell("D12", "Remaining hours"), cell("E12", "=SUM(E2:E10)", "formula")]
        )
        schedule = table(
            "Rehearsals",
            [
                ["Session", "Start", "End"],
                *[[str(i + 1), s["start"], s["end"]] for i, s in enumerate(self.slots())],
            ],
        )
        return {
            "kind": "workbook",
            "filename": "demo-budget.xlsx",
            "sheets": [summary, sheet, tasks_sheet, schedule],
        }

    def report_blocks(self, budget, slots):
        quotes, tasks, _, _, _ = self.data()
        values = grid(budget["result"]["readback"], "Summary")
        selected = values["B18"]["text"]
        total = values["B16"]["value"]
        remaining = [t for t in tasks.values() if t["status"] != "completed"]
        return [
            {"kind": "title", "text": "Group 2 Demo Preparation Brief"},
            {
                "kind": "paragraph",
                "text": "Fictional acceptance dataset - not a school submission or a purchase request. Demo: 6 November 2026, 16:00, Asia/Hong_Kong.",
            },
            {"kind": "heading", "text": "Current position"},
            {
                "kind": "paragraph",
                "text": "The dated task export and later meeting note resolve to nine distinct tasks. T01 and T04 are completed; T02 is reopened. Seven tasks remain, totalling 14.5 hours. Producing this preparation package does not complete that project work.",
            },
            {"kind": "heading", "text": "Budget proposal"},
            {
                "kind": "table",
                "rows": [
                    ["Decision", "Verified worksheet value"],
                    ["Selected supplier", selected],
                    ["Print mode", values["B5"]["text"]],
                    ["Required booklets", str(int(values["B4"]["value"]))],
                    ["Additional minimum-order copies", str(int(values["B19"]["value"]))],
                    ["Total including 10% reserve", f"HKD {total:.2f}"],
                    ["Budget limit", f"HKD {values['B3']['value']:.2f}"],
                ],
            },
            {
                "kind": "paragraph",
                "text": "Prices include the actual minimum quantity, item-only discount, delivery and conversion at the frozen test FX rate. Cedar's current C-2 quote arrives on 7 November, so it is excluded despite its lower price. The older C-1 delivery promise is not current.",
            },
            {
                "kind": "paragraph",
                "text": "The revised request for 40 colour booklets under HKD 1000 has no feasible offer. Black-and-white printing is considered only after the scripted owner clarification. No order or payment has been made."
                if len(self.state["phases"]) > 0
                else "This is the initial colour-print proposal. Recheck constraints and sources before authorizing any later change. No order or payment has been made.",
            },
            {"kind": "page_break"},
            {"kind": "heading", "text": "Remaining work and responsibilities"},
            {
                "kind": "table",
                "rows": [
                    ["Task", "Owner", "Hours", "Dependencies"],
                    *[
                        [
                            t["id"] + " " + t["title"],
                            t["owner"],
                            t["remaining_hours"],
                            t["depends_on"] or "None",
                        ]
                        for t in remaining
                    ],
                ],
            },
            {"kind": "heading", "text": "Rehearsals"},
            {
                "kind": "table",
                "rows": [
                    ["Session", "Start (HKT)", "End (HKT)"],
                    *[
                        [
                            str(i + 1),
                            s["start"][:16].replace("T", " "),
                            s["end"][:16].replace("T", " "),
                        ]
                        for i, s in enumerate(slots)
                    ],
                ],
            },
            {
                "kind": "paragraph",
                "text": "Both 45-minute slots intersect all three members' supplied availability and avoid existing calendar events. A changed second slot updates its original event identity; it does not create another rehearsal.",
            },
            {"kind": "heading", "text": "Sources and remaining limits"},
            {
                "kind": "paragraph",
                "text": "Sources: tasks.csv, meeting-notes.md (29 October, 14:00), availability.csv, existing-events.csv, frozen fx-rates.csv and current quotes "
                + ", ".join(q["id"] for q in quotes.values())
                + ". All people, prices and deadlines are fictional.",
            },
            {
                "kind": "paragraph",
                "text": "The spreadsheet and document were operated through real application APIs, then reopened and checked. This scripted execution-layer run does not establish autonomous voice-agent success, human speech quality, or a real-world delivery commitment. The email remains an unsent local draft.",
            },
        ]

    def publish_documents(self, budget, *, revise=False):
        slots = self.slots(exclude_wednesday=revise)
        previous = dict(self.state["jobs"])
        document = self.step(
            "brief",
            {
                "kind": "document",
                "filename": "demo-brief.odt",
                "source_job_id": previous.get("brief") if revise else None,
                "blocks": self.report_blocks(budget, slots),
            },
            "Prepare the English demo brief",
            depends_on=[budget["id"]],
        )
        self.step(
            "pdf",
            {
                "kind": "pdf",
                "filename": "demo-brief.pdf",
                "source_job_id": document["id"],
                "replace_job_id": previous.get("pdf") if revise else None,
            },
            "Export the checked brief to PDF",
        )
        text = (
            "# Group 2 action plan\n\nFictional test data. Seven source tasks remain (14.5 hours).\n\n"
            + "\n".join(
                f"- Rehearsal {i + 1}: {s['start']} to {s['end']}" for i, s in enumerate(slots)
            )
            + "\n\nNo purchase, payment or email transmission.\n"
        )
        self.step(
            "plan",
            {
                "kind": "text",
                "filename": "action-plan.md",
                "source_job_id": previous.get("plan") if revise else None,
                "text": text,
            },
            "Save the action plan",
        )
        values = grid(budget["result"]["readback"], "Summary")
        email = f"To: tutor@example.invalid\nSubject: Group 2 fictional demo preparation\n\nDraft only. The preparation files are ready for review. The current proposal is {values['B18']['text']}, HKD {values['B16']['value']:.2f} including reserve. Seven project tasks remain. Please see demo-budget.xlsx and demo-brief.pdf.\n\nNo message has been sent.\n"
        self.step(
            "email",
            {
                "kind": "text",
                "filename": "email-draft.txt",
                "source_job_id": previous.get("email") if revise else None,
                "text": email,
            },
            "Save an unsent email draft",
        )

    def initial(self):
        if self.state["phases"]:
            raise ValueError("Initial phase already ran")
        if "task_id" not in self.state:
            task = self.runtime.tasks.create(
                TaskInput(
                    title="Group 2 demo package - scripted execution QA",
                    status="in_progress",
                    follow_up_enabled=False,
                    due_local="2026-11-06T16:00",
                    next_step="Read connected sources and prepare the initial package",
                ),
                "acceptance/task",
            )["task"]
            self.state["task_id"] = task["id"]
            self.save()
        policy = self.runtime.permissions.snapshot()
        if policy["mode"] != "full":
            self.runtime.permissions.change(
                PermissionChange(mode="full", expected_version=policy["version"]),
                "acceptance/full/" + str(policy["version"]),
            )
        self.read_sources()
        _, _, _, _, busy = self.data()
        for item in busy:
            self.runtime.store.create(
                CreateEvents(
                    event=EventInput(
                        title=item["title"],
                        start_local=item["start"][:16],
                        end_local=item["end"][:16],
                        reminder_minutes=[],
                    )
                ),
                "acceptance/" + item["id"],
            )
        budget = self.step("budget", self.workbook(), "Build the initial comparison workbook")
        values = grid(budget["result"]["readback"], "Summary")
        assert values["B18"]["text"] == "Aster" and abs(values["B16"]["value"] - 809.60) < 0.001
        self.state["rehearsals"] = []
        for i, slot in enumerate(self.slots(), 1):
            created = self.runtime.store.create(
                CreateEvents(
                    event=EventInput(
                        title=f"Group 2 rehearsal {i}",
                        start_local=slot["start"][:16],
                        end_local=slot["end"][:16],
                        reminder_minutes=[],
                    )
                ),
                f"acceptance/rehearsal-{i}",
            )
            self.state["rehearsals"].append(created["event_ids"][0])
        self.save()
        self.publish_documents(budget)
        self.state["phases"].append({"phase": "initial", "pid": os.getpid()})
        self.save()
        self.update_task(
            next_step="Initial package prepared; await the planned constraint correction"
        )

    def revise(self):
        if [p["phase"] for p in self.state["phases"]] != ["initial"]:
            raise ValueError("Revision requires exactly the initial phase")
        self.update_task(next_step="Budget 1000, 40 copies, no Wednesday. Recheck feasibility.")
        prior = self.state["jobs"]["budget"]
        revised = self.step(
            "budget",
            {
                "kind": "workbook",
                "filename": "demo-budget.xlsx",
                "source_job_id": prior,
                "sheets": [
                    {"sheet": "Summary", "cells": [cell("B3", 1000), cell("B4", 40)]},
                    {
                        "sheet": "Rehearsals",
                        "cells": [
                            cell("B3", self.slots(True)[1]["start"]),
                            cell("C3", self.slots(True)[1]["end"]),
                        ],
                    },
                ],
            },
            "Recalculate the changed constraints",
        )
        values = grid(revised["result"]["readback"], "Summary")
        assert (
            values["B17"]["text"] == "Clarification needed"
            and values["B18"]["text"] == "No valid option"
        )
        event_id = self.state["rehearsals"][1]
        with self.runtime.store.connection() as conn:
            old = self.runtime.store.event(conn, event_id)
        slot = self.slots(True)[1]
        event = {k: old[k] for k in EventInput.model_fields}
        event.update(start_local=slot["start"][:16], end_local=slot["end"][:16])
        self.runtime.store.event_action(
            event_id,
            EventAction(
                action="update",
                scope="series",
                expected_version=old["version"],
                event=EventInput.model_validate(event),
            ),
            "acceptance/reschedule",
        )
        self.update_task(
            next_step="Current colour offers are infeasible; wait for the print-mode decision",
            status="waiting",
            waiting_for="Owner print-mode clarification",
        )
        self.state["phases"].append(
            {
                "phase": "clarification",
                "pid": os.getpid(),
                "scripted_owner_reply": "Black-and-white is allowed; keep all other constraints.",
            }
        )
        self.save()
        self.update_task(
            next_step="Apply the authorized black-and-white change, then refresh the brief and PDF"
        )
        self.step(
            "budget",
            {
                "kind": "workbook",
                "filename": "demo-budget.xlsx",
                "source_job_id": revised["id"],
                "sheets": [{"sheet": "Summary", "cells": [cell("B5", "black_white")]}],
            },
            "Apply the clarified print mode",
            crash=True,
        )

    def recover(self):
        lost = self.state["lost_result"]
        job = self.runtime.jobs.detail(lost["job_id"], review=True)
        assert job["state"] == "unknown"
        assert any(entry["code"] == "PROCESS_RESTARTED" for entry in job["history"])
        path = self.runtime.jobs.applications.target(job["request"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == lost["sha256"]
        result = self.runtime.jobs.reconcile(job["id"])["job"]
        assert result["state"] == "succeeded" and path.stat().st_mtime_ns == lost["mtime_ns"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == lost["sha256"]
        budget = self.runtime.jobs.detail(job["id"], review=True)
        values = grid(budget["result"]["readback"], "Summary")
        assert values["B18"]["text"] == "Delta" and abs(values["B16"]["value"] - 669.24) < 0.001
        assert values["B19"]["value"] == 10
        self.state["phases"].append(
            {"phase": "recovered", "pid": os.getpid(), "same_file_hash_and_mtime": True}
        )
        self.save()
        self.publish_documents(budget, revise=True)
        with self.runtime.store.connection() as conn:
            events = [
                self.runtime.store.event(conn, event_id) for event_id in self.state["rehearsals"]
            ]
            count = conn.execute("SELECT COUNT(*) FROM events WHERE deleted=0").fetchone()[0]
        assert count == 5 and events[0]["version"] == 1 and events[1]["version"] == 2
        assert events[1]["start_local"].startswith("2026-11-05T15:15")
        current = self.task()
        grant = self.runtime.permissions.capture(self.principal, current["id"])
        pending = self.runtime.jobs.prepare(
            ApplicationJobInput(
                title="Revocation check",
                task_id=current["id"],
                task_version=current["version"],
                stage="revocation-check",
                step={
                    "kind": "text",
                    "filename": "must-not-publish.txt",
                    "text": "This queued revision must be blocked.",
                },
            ),
            "acceptance/revocation-draft",
        )
        self.runtime.permissions.apply_reply(pending, grant)
        policy = self.runtime.permissions.snapshot()
        self.runtime.permissions.change(
            PermissionChange(mode="ask", expected_version=policy["version"]), "acceptance/revoke"
        )
        self.runtime.jobs.run_one()
        rejected = self.runtime.jobs.detail(pending["job"]["id"], review=True)
        assert rejected["error"] == "PERMISSION_CHANGED"
        assert not self.runtime.jobs.applications.target(rejected["request"]).exists()
        self.update_task(
            next_step="Execution-layer artifacts verified; model-driven and human voice acceptance remain open"
        )
        exported = {}
        for stage in ("budget", "brief", "pdf", "plan", "email"):
            filename, body = self.runtime.jobs.application_download(self.state["jobs"][stage])
            target = self.report / "artifacts" / filename
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(body)
            exported[stage] = {
                "filename": filename,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }
        report = {
            "layer": "scripted real-application execution",
            "model_calls": 0,
            "autonomous_agent_pass": False,
            "task": self.task(),
            "stages": self.runtime.jobs.application_state(self.state["task_id"]),
            "phases": self.state["phases"],
            "rehearsals": events,
            "calendar_count": count,
            "revocation": {"state": rejected["state"], "error": rejected["error"]},
            "artifacts": exported,
            "final_permissions": self.runtime.permissions.snapshot(),
        }
        (self.report / "acceptance-result.json").write_text(json.dumps(report, indent=2) + "\n")
        self.state["phases"].append({"phase": "complete", "pid": os.getpid()})
        self.save()
        print(
            json.dumps(
                {"completed_execution_layer": True, "artifacts": exported, "model_calls": 0}
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=["initial", "revise", "recover"])
    parser.add_argument("--run-real-apps", action="store_true")
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if not args.run_real_apps:
        parser.error(
            "Use --run-real-apps only in the configured disposable application environment"
        )
    for key in ("DESK_TEXT_PROVIDER", "DESK_VOICE_PROVIDER"):
        os.environ[key] = "none"
    for key in (
        "DESK_TEXT_BACKGROUND",
        "DESK_MEMORY_EXTRACT",
        "DESK_WEB_PUSH",
        "DESK_COMPUTER_ENABLED",
        "DESK_LINUX_DESKTOP_ENABLED",
    ):
        os.environ[key] = "0"
    controller = Controller(args.runtime.resolve(), args.report.resolve(), args.attempt)
    getattr(controller, args.phase)()


if __name__ == "__main__":
    main()
