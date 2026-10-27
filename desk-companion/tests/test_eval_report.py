"""The offline report lists every scripted suite and does not call a provider."""

import subprocess
import sys
from pathlib import Path

from desk.conversation_eval import cases
from desk.eval_report import EvalRow, collect, format_table, summary

from test_agent_loop import _runtime


def test_table_marks_a_failure_on_one_line():
    text = format_table(
        [EvalRow("agent", "scenario_x", False, "AssertionError: boom\nnext")]
    )
    assert text.splitlines()[0] == f"{'suite':<14} {'name':<36} result"
    assert "scenario_x" in text
    assert "fail AssertionError: boom next" in text
    assert "\nnext" not in text
    assert summary([EvalRow("agent", "scenario_x", False, "x")]) == "0 passed, 1 failed"


def test_collect_runs_every_offline_suite(tmp_path):
    rows = collect(lambda: _runtime(tmp_path))
    assert [row.name for row in rows if row.suite == "agent"] == [
        "scenario_remind",
        "scenario_recall",
        "scenario_refuse",
        "scenario_approval",
        "scenario_step_bound",
        "scenario_time_bound",
        "scenario_provider_retry",
        "scenario_voice_same_policy",
    ]
    assert [row.name for row in rows if row.suite == "conversation"] == [
        case.name for case in cases()
    ]
    assert [row.name for row in rows if row.suite == "retrieval"] == [
        "scenario_english_overlap_beats_recency",
        "scenario_chinese_bigram",
        "scenario_newer_tie_wins",
        "scenario_search_does_not_write",
    ]
    assert rows
    assert all(row.passed for row in rows)
    assert summary(rows).endswith("0 failed")
    table = format_table(rows)
    assert len(table.splitlines()) == len(rows) + 1


def test_script_exits_zero_without_a_live_provider():
    completed = subprocess.run(
        [sys.executable, "scripts/tool_eval.py"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "scenario_refuse" in completed.stdout
    assert "scenario_chinese_bigram" in completed.stdout
    assert "persona_who_zh" in completed.stdout
    assert completed.stdout.strip().endswith("0 failed")
    assert "DESK_CONVERSATION_EVAL" not in completed.stdout
