"""Offline scenarios for memory recall and check-in timing. No model and no network."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from desk.nudges import due_kinds
from desk.runtime import Runtime
from desk.store import Store
from desk.workspace_data import WorkspacePreferences

SCENARIOS = json.loads(
    (Path(__file__).parents[1] / "evals" / "memory_proactivity.json").read_text(encoding="utf-8")
)


def test_memory_recall_scenarios(tmp_path):
    for index, scenario in enumerate(SCENARIOS["recall"]):
        clock = [datetime(2026, 10, 2, tzinfo=UTC)]
        runtime = Runtime(
            Store(
                tmp_path / str(index),
                password="fixture-only",
                clock=lambda clock=clock: clock[0],
            )
        )
        saved = {}
        for step in scenario["steps"]:
            clock[0] += timedelta(seconds=1)
            if "save" in step:
                created = runtime.memory.create(
                    step["save"], uuid4().hex, expires_at=step.get("expires_at")
                )["memory"]
                saved[created["body"]] = created
            elif "delete" in step:
                fact = saved[step["delete"]]
                runtime.memory.delete(fact["id"], fact["version"], uuid4().hex)
            elif step.get("confirm_suggestion"):
                suggestion = runtime.memory.listing()["suggestions"][0]
                draft = runtime.memory.prepare_consolidation(
                    suggestion["keep"]["id"],
                    [row["id"] for row in suggestion["retire"]],
                    uuid4().hex,
                )
                runtime.assistant.decide(draft["proposal"]["id"], "confirm", uuid4().hex)
        visible = {row["body"] for row in runtime.memory.for_model()}
        assert set(scenario["present"]) <= visible, scenario["name"]
        assert visible.isdisjoint(scenario["absent"]), scenario["name"]


def test_proactive_timing_scenarios():
    for scenario in SCENARIOS["timing"]:
        prefs = WorkspacePreferences().model_dump()
        prefs.update(scenario["preferences"])
        prefs = WorkspacePreferences.model_validate(prefs).model_dump()
        now = datetime.fromisoformat(scenario["now"]).astimezone(ZoneInfo(scenario["zone"]))
        assert due_kinds(prefs, now) == scenario["kinds"], scenario["name"]
