"""Run in each pinned backend, using the same public fixtures and an empty private desk."""

from datetime import UTC, datetime
import json
from importlib.util import find_spec
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from desk.app import create_app
from session_protocol_fixture import install_session_protocol

CASES = (
    ("ordinary", "Please greet the fixture."),
    ("tokyo", "帮我查一下东京的天气"),
    ("google", "What changed in my Google Calendar just now?"),
    ("approval", "What needs my approval?"),
    ("quiet", "What changed while I was away?"),
    ("work", "continue the task from before"),
    ("real_ticket", "帮我购买这个机票"),
    ("written_hkd", "请说明这项测试数据"),
)


def read_cases():
    with TemporaryDirectory() as directory:
        app = create_app(Path(directory), password="synthetic-only", scheduler=False, connector_configs=(),
                         clock=lambda: datetime(2026, 11, 22, 15, 30, tzinfo=UTC))
        runtime = app.state.runtime
        model = install_session_protocol(runtime)
        if find_spec("desk.weather_conversation"):
            from desk.weather import WeatherService
            from test_global_weather import NOW, fixture_weather
            runtime.data.weather_provider = WeatherService(fixture_weather, now=lambda: NOW)
        report = {}
        with TestClient(app, headers={"X-Desk-Request": "1"}) as client:
            client.post("/api/session", json={"username": "owner", "password": "synthetic-only"}).raise_for_status()
            for key, words in CASES:
                modeled = "Scoped offline control." if key != "written_hkd" else "报价是港币三千三百八十九元五角九仙。"
                model.final = json.dumps({"delivery": "neutral", "message": modeled}, ensure_ascii=False)
                before_model = len(model.requests)
                response = client.post("/api/assistant/messages", headers={"X-Operation-Id": "control-" + key},
                                       json={"message": words, "language": "zh" if key in {"tokyo", "written_hkd", "real_ticket"} else "en"})
                response.raise_for_status()
                reply = response.json()
                report[key] = {
                    "kind": reply["kind"], "message": reply["message"], "used_model": len(model.requests) != before_model,
                    "saved": bool(reply.get("saved")), "checkout": (reply.get("live_flight_checkout") or {}).get("state"),
                }
            with runtime.store.connection() as db:
                names = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
                report["business_rows"] = {
                    table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    for table in ("events", "tasks", "agent_runs", "computer_jobs", "sandbox_shop_orders", "sandbox_flight_bookings")
                    if table in names
                }
        return report


def compare(directory):
    reports = {name: json.loads((directory / (name + "-responses.json")).read_text())
               for name in ("stable", "personal", "final", "combined")}
    origins = {"ordinary": "stable", "tokyo": "final", "google": "personal", "approval": "personal",
               "quiet": "personal", "work": "personal", "real_ticket": "final", "written_hkd": "final"}
    answer = {}
    for case, parent in origins.items():
        actual = reports["combined"][case]
        assert actual == reports[parent][case], (case, parent, actual)
        answer[case] = {"matches": parent, **actual}
    assert all(not any(v["business_rows"].values()) for v in reports.values())
    assert "73%" in answer["tokyo"]["message"] and not answer["tokyo"]["used_model"]
    assert "HK$3,389.59" in answer["written_hkd"]["message"]
    assert "五角九仙" in reports["stable"]["written_hkd"]["message"]
    assert answer["real_ticket"]["checkout"] == "no_source"
    return answer


if __name__ == "__main__":
    result = compare(Path(sys.argv[2])) if sys.argv[1] == "--compare" else read_cases()
    Path(sys.argv[-1]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
