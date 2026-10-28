"""The profile is a bounded, deterministic summary of confirmed facts."""

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from desk.app import create_app
from desk.context import pack_conversation
from desk.profile import BUDGET, assemble
from desk.runtime import Runtime
from desk.store import Store


def test_profile_scenarios_are_stable():
    path = Path(__file__).parents[1] / "evals" / "profile_continuity.json"
    scenarios = json.loads(path.read_text())["scenarios"]
    long_facts = [
        {"id": f"{index:032x}", "body": f"I prefer item {index:02d} " + ("x" * 80), "note": "preference"}
        for index in range(30)
    ]
    for scenario in scenarios:
        facts = long_facts if scenario.get("budget_only") else scenario["facts"]
        first = assemble(facts, scenario["goals"], set(scenario["omit"]))
        second = assemble(facts, scenario["goals"], set(scenario["omit"]))
        assert first == second
        assert len(first["text"]) <= BUDGET
        for needle in scenario["contains"]:
            assert needle in first["text"]
        for needle in scenario["absent"]:
            assert needle not in first["text"]
        if scenario.get("order"):
            earlier, later = scenario["order"]
            assert first["text"].index(earlier) < first["text"].index(later)
        if scenario.get("budget_only"):
            assert "I prefer item 29" not in first["text"]


def test_confirmed_facts_enter_the_prompt_until_omitted_or_deleted(tmp_path):
    runtime = Runtime(
        Store(tmp_path, password="fixture-only", clock=lambda: datetime(2026, 10, 27, tzinfo=UTC))
    )
    fact = runtime.memory.create("I prefer tea", "save", note="preference")["memory"]
    assert "Preferences: I prefer tea" in pack_conversation(runtime)["profile"]
    runtime.profile.omit(fact["id"], "omit")
    assert pack_conversation(runtime)["profile"] == ""
    assert runtime.memory.for_model()[0]["body"] == "I prefer tea"
    runtime.profile.restore(fact["id"], "restore")
    runtime.memory.delete(fact["id"], fact["version"], "forget")
    assert pack_conversation(runtime)["profile"] == ""
    assert pack_conversation(runtime, include_memory=False)["profile"] == ""


def test_display_cannot_read_the_profile(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    owner = TestClient(app)
    owner.post(
        "/api/session",
        json={"username": "owner", "password": "fixture-only"},
        headers={"X-Desk-Request": "1"},
    )
    owner.post(
        "/api/devices/enrol-display",
        json={"name": "Shared display"},
        headers={"X-Desk-Request": "1", "X-Operation-Id": "pair-profile"},
    )
    display = TestClient(app)
    display.headers.update(
        {
            "Authorization": "Bearer " + owner.cookies.get("desk_companion_device"),
            "X-Desk-Request": "1",
        }
    )
    assert display.get("/api/profile").status_code == 403
