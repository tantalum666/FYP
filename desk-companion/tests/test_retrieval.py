"""Ranked search and memory recall. No network."""

from desk.rank import rank_rows, tokens
from desk.retrieval_eval import run_all

from test_agent_loop import _runtime


def test_tokens_cover_english_and_chinese_pairs():
    assert tokens("Pack the Lantern") == ("pack", "the", "lantern")
    assert tokens("红灯笼") == ("红", "灯", "笼", "红灯", "灯笼")
    assert tokens("") == ()


def test_same_inputs_rank_the_same_way():
    rows = [
        {"id": "b", "time": "2026-10-02", "text": "lantern dark", "payload": "b"},
        {"id": "a", "time": "2026-10-27", "text": "lantern", "payload": "a"},
    ]
    assert rank_rows("lantern dark", rows, limit=8) == rank_rows("lantern dark", rows, limit=8)
    assert rank_rows("lantern dark", rows, limit=8) == ["b", "a"]


def test_ranked_scenarios(tmp_path):
    results = run_all(lambda: _runtime(tmp_path))
    assert [result.name for result in results] == [
        "scenario_english_overlap_beats_recency",
        "scenario_chinese_bigram",
        "scenario_newer_tie_wins",
        "scenario_search_does_not_write",
    ]
    failed = [result for result in results if not result.passed]
    assert not failed
