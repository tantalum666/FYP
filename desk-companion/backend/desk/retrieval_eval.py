"""Offline ranking scenarios. No network.

These stay out of agent_eval.run_all so that list does not change.
"""

from .agent_eval import ScenarioResult
from .agent_loop import AgentLoop
from .model_provider import ModelStep, ScriptedProvider


def run_all(new_runtime) -> list[ScenarioResult]:
    results = []
    for scenario in (
        scenario_english_overlap_beats_recency,
        scenario_chinese_bigram,
        scenario_newer_tie_wins,
        scenario_search_does_not_write,
    ):
        try:
            scenario(new_runtime)
        except Exception as error:
            results.append(ScenarioResult(scenario.__name__, False, f"{type(error).__name__}: {error}"))
        else:
            results.append(ScenarioResult(scenario.__name__, True, ""))
    return results


def scenario_english_overlap_beats_recency(new_runtime):
    runtime = new_runtime()
    older = runtime.memory.create("Pack the lantern before dark.", "older-fact")["memory"]
    newer = runtime.memory.create("The lantern is packed.", "newer-fact")["memory"]
    _stamp(runtime, older["id"], "2026-10-01T00:00:00+00:00")
    _stamp(runtime, newer["id"], "2026-10-27T00:00:00+00:00")
    found = runtime.assistant.tool(
        "owner_search", {"query": "lantern dark", "sources": ["memory"]}, "rank-en"
    )
    if [row["id"] for row in found["matches"]] != [older["id"], newer["id"]]:
        raise AssertionError(found)
    recalled = runtime.assistant.tool("memory_query", {"query": "lantern dark"}, "rank-recall")
    if [row["body"] for row in recalled["memories"]] != [
        "Pack the lantern before dark.",
        "The lantern is packed.",
    ]:
        raise AssertionError(recalled)
    if len(runtime.memory.for_model()) != 2:
        raise AssertionError("ranking wrote memory")


def scenario_chinese_bigram(new_runtime):
    runtime = new_runtime()
    hit = runtime.memory.create("晚上要带红灯笼。", "zh-hit")["memory"]
    runtime.memory.create("苹果放在桌上。", "zh-miss")
    found = runtime.assistant.tool(
        "memory_query", {"query": "灯笼"}, "rank-zh"
    )
    bodies = [row["body"] for row in found["memories"]]
    if bodies != ["晚上要带红灯笼。"]:
        raise AssertionError(bodies)
    if found["memories"][0]["id"] != hit["id"]:
        raise AssertionError(found)


def scenario_newer_tie_wins(new_runtime):
    runtime = new_runtime()
    older = runtime.memory.create("The code word is lantern.", "tie-old")["memory"]
    newer = runtime.memory.create("The code word is lantern.", "tie-new")["memory"]
    _stamp(runtime, older["id"], "2026-10-01T00:00:00+00:00")
    _stamp(runtime, newer["id"], "2026-10-20T00:00:00+00:00")
    found = runtime.assistant.tool("memory_query", {"query": "lantern"}, "rank-tie")
    if [row["id"] for row in found["memories"]] != [newer["id"], older["id"]]:
        raise AssertionError(found)


def scenario_search_does_not_write(new_runtime):
    runtime = new_runtime()
    runtime.memory.create("The project code is lantern.", "recall-fact")
    provider = ScriptedProvider(
        [
            ModelStep("I will search.", "owner_search", {"query": "lantern", "sources": ["memory"]}),
            ModelStep("The project code is lantern.", "none", {}),
        ]
    )
    reply = AgentLoop(runtime, provider).run(
        system="Desk Companion",
        context={},
        key="rank-loop",
        language="en",
        allow_memory=True,
    )
    if reply["message"] != "The project code is lantern." or provider.calls != 2:
        raise AssertionError(reply)
    if runtime.assistant.proposals():
        raise AssertionError("search created a draft")
    with runtime.store.connection() as conn:
        events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if events:
        raise AssertionError("search wrote an event")


def _stamp(runtime, memory_id, when):
    with runtime.store.connection(write=True) as conn:
        conn.execute(
            "UPDATE owner_memories SET updated_at=? WHERE id=?",
            (when, memory_id),
        )
