"""Saved tone, verbosity, and proactivity change prompts and local replies."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from desk.app import create_app
from desk.assistant import AssistantMessage
from desk.style import persona_problems, render_prompt, shape
from desk.text_ai import TextAssistant, TextConfig, TextPlan
from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"


def _prefs(runtime, **fields):
    current = runtime.data.preferences()
    runtime.data.update(
        PreferencesUpdate(
            expected_version=current["version"],
            preferences=WorkspacePreferences(**fields),
        ),
        uuid4().hex,
    )


def test_offline_style_scenarios_keep_the_persona_ahead_of_style():
    path = Path(__file__).parents[1] / "evals" / "persona_style.json"
    scenarios = json.loads(path.read_text(encoding="utf-8"))["scenarios"]
    assert {row["language"] for row in scenarios} == {"en", "zh"}
    for scenario in scenarios:
        prefs = {
            "tone": scenario["tone"],
            "verbosity": scenario["verbosity"],
            "proactivity": scenario["proactivity"],
        }
        prompt = render_prompt(scenario["persona"], prefs, scenario["language"])
        again = render_prompt(scenario["persona"], prefs, scenario["language"])
        assert prompt == again
        assert persona_problems(scenario["persona"], prompt, scenario["language"]) == []
        spoken = render_prompt(
            scenario["persona"],
            prefs,
            scenario["language"],
            channel="voice",
            now_iso="2026-10-27T10:00:00+08:00",
            zone="Asia/Hong_Kong",
        )
        assert persona_problems(scenario["persona"], spoken, scenario["language"]) == []
        reply = shape(scenario["message"], prefs, scenario["language"])
        for needle in scenario["contains"]:
            assert needle in reply
        for needle in scenario["absent"]:
            assert needle not in reply


def test_local_chat_and_a_configured_prompt_follow_the_saved_style(tmp_path):
    app = create_app(tmp_path, password="fixture-only", scheduler=False)
    client = TestClient(app)
    assert (
        client.post(
            "/api/session",
            json={"username": "owner", "password": "fixture-only"},
            headers={"X-Desk-Request": "1"},
        ).status_code
        == 200
    )
    runtime = app.state.runtime
    _prefs(runtime, tone="warm", verbosity="brief", proactivity="off")
    local = runtime.assistant.local_message(AssistantMessage(message="hello there"), "local-style")
    assert local["message"].startswith("Sure — ")
    assert "You can also ask" not in local["message"]
    zh = runtime.assistant.local_message(
        AssistantMessage(message="随便说说", language="zh"),
        "local-style-zh",
    )
    assert zh["message"].startswith("好，")
    assert "也可以查询" not in zh["message"]

    seen = {}

    def generate(system, _context, _schema, _purpose):
        seen["system"] = system
        return TextPlan(message="Noted. Want to start the report?", tool="none")

    service = TextAssistant(
        runtime,
        TextConfig("qwen", "test-model", ENDPOINT, "fixture-key"),
        httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    service.generate = generate
    reply = service.message(AssistantMessage(message="hello there"), "model-style")
    assert "Want to start" not in reply["message"]
    assert reply["message"].startswith("Sure — ")
    body = runtime.persona.current()["body"]
    assert persona_problems(body, seen["system"], "en") == []
