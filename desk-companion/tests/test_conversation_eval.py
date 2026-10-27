"""Offline conversation checks. The live script is invoked only to prove it refuses."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from desk.conversation_eval import (
    check_clarify,
    check_persona,
    check_refuse,
    live_enabled,
    run_capped,
    run_scripted,
)
from desk.model_provider import ModelStep
from desk.tool_policy import owner_message

from test_agent_loop import _runtime


ROOT = Path(__file__).resolve().parents[1]


def test_scripted_cases_cover_persona_refusal_and_one_question(tmp_path):
    results = run_scripted(lambda: _runtime(tmp_path))
    failed = [result for result in results if not result.passed]
    assert [result.name for result in results] == [
        "persona_who_en",
        "persona_who_zh",
        "persona_not_chatgpt_en",
        "persona_not_muse_zh",
        "refuse_shell_en",
        "refuse_shell_zh",
        "refuse_email_en",
        "refuse_email_zh",
        "refuse_browser_en",
        "refuse_browser_zh",
        "clarify_move_en",
        "clarify_change_zh",
        "clarify_tomorrow_en",
        "clarify_remind_zh",
        "bilingual_persona_zh",
        "bilingual_refuse_zh",
        "bilingual_clarify_en",
    ]
    assert not failed
    assert owner_message("refused", "zh").startswith("这个动作不在助理可用的工具里")


def test_checkers_reject_another_product_and_two_questions(tmp_path):
    runtime = _runtime(tmp_path)
    with pytest.raises(AssertionError):
        check_persona(
            "You are Desk Companion.",
            {"kind": "reply", "message": "I am ChatGPT.", "saved": False},
        )
    with pytest.raises(AssertionError):
        check_persona(
            "You are a helper.",
            {"kind": "reply", "message": "I am Desk Companion.", "saved": False},
        )
    with pytest.raises(AssertionError):
        check_clarify(
            {"kind": "reply", "message": "Which one? Or this one?", "saved": False},
            runtime,
        )
    with pytest.raises(AssertionError):
        check_refuse(
            {"kind": "reply", "message": "Done.", "saved": True},
            runtime,
            "en",
        )


def test_live_gate_stays_shut_without_every_explicit_setting():
    assert live_enabled({})[0] is False
    assert live_enabled({"DESK_CONVERSATION_EVAL": "1"})[0] is False
    assert live_enabled({"DESK_CONVERSATION_EVAL": "1", "DESK_CONVERSATION_EVAL_CAP": "0"})[0] is False
    assert live_enabled({"DESK_CONVERSATION_EVAL": "1", "DESK_CONVERSATION_EVAL_CAP": "25"})[0] is False
    assert live_enabled({"DESK_CONVERSATION_EVAL": "1", "DESK_CONVERSATION_EVAL_CAP": "nope"})[0] is False
    shut, reason = live_enabled({"DESK_CONVERSATION_EVAL": "1", "DESK_CONVERSATION_EVAL_CAP": "3"})
    assert shut is False and "not configured" in reason
    opened, detail = live_enabled(
        {
            "DESK_CONVERSATION_EVAL": "1",
            "DESK_CONVERSATION_EVAL_CAP": "3",
            "DESK_TEXT_PROVIDER": "qwen",
            "DESK_TEXT_MODEL": "qwen-test",
            "DESK_TEXT_ENDPOINT": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "DESK_TEXT_API_KEY": "test-key",
        }
    )
    assert opened is True and detail == ""


def test_cap_stops_before_another_provider_call(tmp_path):
    calls = []

    def bind(_runtime):
        def complete(system, context):
            calls.append(system)
            return ModelStep("I am Desk Companion.", "none", {})

        return complete

    results, used = run_capped(lambda: _runtime(tmp_path), bind, 1)
    assert used == 1 and len(calls) == 1
    assert "Desk Companion" in calls[0]
    assert results[0].name == "persona_who_en" and results[0].passed and results[0].detail == ""
    assert all(result.detail == "skipped: cap" for result in results[1:])


def test_script_refuses_without_the_live_env():
    script = ROOT / "scripts" / "conversation_eval.py"
    env = {key: value for key, value in os.environ.items() if not key.startswith("DESK_")}
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert "Refusing:" in result.stdout
    assert result.stderr == ""
