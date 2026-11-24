import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import json
import threading
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
import pytest

from desk.app import create_app
from desk.openai_live import OPENAI_LIVE_ENDPOINT
from desk.voice import VoiceConfig
from desk.weather import WeatherQuery, WeatherService
from desk.weather_conversation import direct_query
from desk.weather_forecast import DAILY, HOURLY
from session_protocol_fixture import install_session_protocol
from voice_fixtures import Provider, Socket


# HK is still on the 22nd; Tokyo is already on the 23rd.
NOW = datetime(2026, 11, 22, 15, 30, tzinfo=UTC)
JAPAN = {
    "id": 1,
    "name": "東京",
    "latitude": 35.69,
    "longitude": 139.69,
    "country": "日本",
    "country_code": "JP",
    "timezone": "Asia/Tokyo",
    "feature_code": "PPLC",
    "population": 9_000_000,
}


def model_data(params, *, now=NOW):
    zone = ZoneInfo(params["timezone"] if params["timezone"] != "auto" else "Asia/Tokyo")
    midnight = now.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    days = params["forecast_days"]
    dates = [int((midnight + timedelta(days=i)).timestamp()) for i in range(days)]
    hours = [int(midnight.timestamp()) + 3600 * i for i in range(24 * days)]
    daily = {
        "time": dates,
        "temperature_2m_min": [6] * days,
        "temperature_2m_max": [13] * days,
        "weather_code": [61] * days,
        "precipitation_probability_max": [73] * days,
        "precipitation_sum": [2.2] * days,
    }
    return {
        "timezone": zone.key,
        "current_units": {"temperature_2m": "°C", "weather_code": "wmo code", "time": "unixtime"},
        "current": {"temperature_2m": 9.5, "weather_code": 3, "time": int(now.timestamp())},
        "daily_units": {"time": "unixtime", **DAILY},
        "daily": daily,
        "hourly_units": {"time": "unixtime", **HOURLY},
        "hourly": {
            "time": hours,
            "precipitation_probability": [73] * len(hours),
            "precipitation": [1.1 if i % 24 in (4, 5) else 0 for i in range(len(hours))],
        },
    }


def fixture_weather(url, params):
    if "/search" in url:
        if params["name"] in {"Tokyo", "東京"}:
            return {"results": [JAPAN]}
        if params["name"] == "东京":
            return {
                "results": [
                    {
                        **JAPAN,
                        "id": 2,
                        "country_code": "CN",
                        "name": "东京",
                        "feature_code": "PPL",
                        "population": 430,
                        "timezone": "Asia/Shanghai",
                    }
                ]
            }
        return {}
    assert "open-meteo.com/v1/forecast" in url
    return model_data(params)


def login(app):
    client = TestClient(app)
    assert client.post(
        "/api/session",
        json={"username": "owner", "password": "fixture"},
        headers={"X-Desk-Request": "1"},
    ).is_success
    return client


def send(client, key, message, *, stream=False):
    response = client.post(
        "/api/assistant/messages" + ("/stream" if stream else ""),
        json={"message": message},
        headers={"X-Desk-Request": "1", "X-Operation-Id": key},
    )
    assert response.is_success
    if not stream:
        return response.json(), []
    events = [
        json.loads(line[5:]) for line in response.text.splitlines() if line.startswith("data:")
    ]
    return next(e["reply"] for e in events if e["type"] == "done"), events


def test_ordinary_city_questions_resolve_before_a_model_call_and_do_not_change_home(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    runtime.data.weather_provider = WeatherService(fixture_weather, now=lambda: NOW)
    official = install_session_protocol(runtime)
    client = login(app)
    for i, prompt in enumerate(
        ("帮我查一下东京的天气", "幫我看一下東京的天氣", "What's the weather in Tokyo today?")
    ):
        reply, events = send(client, f"weather-{i}", prompt, stream=bool(i))
        assert all(x in reply["message"] for x in ("2026-11-23", "9.5°C", "73%", "03:00–05:00"))
        if events:
            assert [(x["phase"], x["tool"]) for x in events if x["type"] == "tool"] == [
                ("started", "weather_query"),
                ("finished", "weather_query"),
            ]
    assert not official.creations and not runtime.data.read_weather()["available"]
    assert runtime.data.preferences()["weather_location"] == "none"
    assert all("location" not in row["arguments"] for row in runtime.assistant.audit.listing(8))


def test_local_dates_explicit_forecast_and_partial_rain_data():
    service = WeatherService(fixture_weather, now=lambda: NOW)
    out = service.query(WeatherQuery(location="Tokyo", start_date="tomorrow", days=3))
    assert "current" not in out and [d["date"] for d in out["days"]] == [
        "2026-11-24",
        "2026-11-25",
        "2026-11-26",
    ]
    assert (
        service.query(WeatherQuery(location="Tokyo", start_date="2026-11-22"))["status"]
        == "out_of_range"
    )
    assert service.query(WeatherQuery(period="today"))["status"] == "missing_city"

    def absent(url, params):
        d = fixture_weather(url, params)
        if "daily" in d:
            d["daily"]["precipitation_probability_max"][0] = None
            d["daily"]["precipitation_sum"][0] = None
        return d

    day = WeatherService(absent, now=lambda: NOW).query(
        WeatherQuery(location="Tokyo", period="today")
    )["days"][0]
    assert "peak_precipitation_probability_pct" not in day and "precipitation_mm" not in day


def test_same_day_hko_uses_official_outlook_not_tomorrow_or_historical_rain():
    def source(url, params):
        if "dataType" not in params:
            return model_data(params)
        if params["dataType"] == "rhrread":
            return {
                "temperature": {
                    "recordTime": NOW.isoformat(),
                    "data": [{"place": "Hong Kong Observatory", "value": 24, "unit": "C"}],
                },
                "rainfall": {"data": [{"max": 99, "unit": "mm"}]},
            }
        if params["dataType"] == "flw":
            return {
                "updateTime": NOW.isoformat(),
                "forecastPeriod": "本港地区今晚天气预测",
                "forecastDesc": "今晚有几阵雨。",
            }
        return {
            "updateTime": NOW.isoformat(),
            "weatherForecast": [
                {
                    "forecastDate": "20261123",
                    "forecastMintemp": {"value": 11, "unit": "C"},
                    "forecastMaxtemp": {"value": 20, "unit": "C"},
                    "forecastWeather": "明天多云",
                    "PSR": "中高",
                }
            ],
        }

    service = WeatherService(source, now=lambda: NOW)
    output = service.query(WeatherQuery(location="香港", period="current", language="zh"))
    assert output["current"]["temperature_c"] == 24 and output["current"]["basis"] == "station"
    assert output["days"][0]["source"] == "Open-Meteo" and "今晚有几阵雨" in output["summary"]
    assert "明天多云" not in output["summary"] and "99" not in output["summary"]
    tomorrow = service.query(WeatherQuery(location="香港", start_date="tomorrow", language="zh"))
    assert (
        tomorrow["days"][0]["significant_rain_category"] == "中高"
        and "%" not in tomorrow["summary"]
    )


def test_geographic_ambiguity_countries_qualifiers_coordinates_and_lookup_failure():
    calls = []

    def lookup(url, params):
        calls.append((url, params))
        if "/search" not in url:
            return model_data(params)
        if params["name"] == "Japan":
            return {"results": [{**JAPAN, "feature_code": "PCLI", "name": "Japan"}]}
        if params["name"].startswith("Springfield"):
            states = ["Illinois", "Missouri"] if "," not in params["name"] else ["Illinois"]
            return {
                "results": [
                    {
                        **JAPAN,
                        "id": i + 1,
                        "name": "Springfield",
                        "country": "United States",
                        "country_code": "US",
                        "timezone": "America/Chicago",
                        "admin1": s,
                        "population": 110000 + i,
                    }
                    for i, s in enumerate(states)
                ]
            }
        return {}

    service = WeatherService(lookup, now=lambda: NOW)
    for location, reason in [
        ("Missingplacefixture", "not_found"),
        ("Japan", "specify_city"),
        ("Springfield", "ambiguous"),
        ("Springfield, Illinois, France", "not_found"),
        ("91, 140", "invalid_coordinates"),
    ]:
        out = service.query(WeatherQuery(location=location))
        assert not out["available"] and out["status"] == reason
    assert not any("/forecast" in u for u, _ in calls)
    result = service.query(
        WeatherQuery(location="Springfield, Illinois", country_code="us", period="today")
    )
    assert result["country_code"] == "US" and result["region"] == "Illinois"
    assert any(p.get("countryCode") == "US" for _, p in calls)
    result = service.query(WeatherQuery(location="35.6873, 139.6921", period="today"))
    assert (
        result["available"]
        and calls[-1][1]["latitude"] == 35.7
        and calls[-1][1]["longitude"] == 139.7
    )


@pytest.mark.parametrize("fault", ["old", "units", "days"])
def test_old_or_inconsistent_global_data_has_no_live_claim(fault):
    def fetch(url, params):
        d = fixture_weather(url, params)
        if "daily" in d:
            if fault == "old":
                d["daily"]["time"][0] -= 86400
            elif fault == "units":
                d["daily_units"]["precipitation_probability_max"] = "mm"
            else:
                d["hourly"]["precipitation"] = []
        return d

    out = WeatherService(fetch, now=lambda: NOW).query(
        WeatherQuery(location="Tokyo", period="today")
    )
    assert not out["available"] and "current" not in out
    if fault == "old":
        assert out["status"] == "stale" and "2026-11-22" in out["summary"]


def test_shared_cache_coalesces_one_outstanding_read():
    entered, release = threading.Event(), threading.Event()
    calls = []

    def load(*args):
        calls.append(args)
        entered.set()
        assert release.wait(3)
        return {"same": True}

    svc = WeatherService(load)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(svc._read, "fixture", {"id": 1})
        assert entered.wait(3)
        second = pool.submit(svc._read, "fixture", {"id": 1})
        release.set()
        assert first.result() == second.result() == {"same": True}
    assert len(calls) == 1


def test_complex_weather_remains_on_sessions_and_keeps_useful_multi_day_results(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    runtime.data.weather_provider = WeatherService(fixture_weather, now=lambda: NOW)
    api = install_session_protocol(runtime)
    args = {"location": "Tokyo", "period": "forecast", "days": 7, "language": "en"}
    api.next_calls = [("weather_query", args)]

    def answer():
        if api.functions:
            value = json.loads(api.functions[-1][0][0]["output"])
            api.final = json.dumps({"message": value["summary"], "delivery": "neutral"})

    api.on_check = answer
    reply, events = send(
        login(app),
        "week-sessions",
        "I am planning a week in Japan. Could you check the daily Tokyo forecast for that trip?",
        stream=True,
    )
    schema = next(t for t in api.creations[0]["agent"]["tools"] if t["name"] == "weather_query")[
        "parameters"
    ]
    assert {"location", "period", "language"} <= set(schema["required"])
    assert {"country_code", "start_date", "days"} <= set(schema["properties"])
    assert [x["phase"] for x in events if x.get("tool") == "weather_query"] == [
        "started",
        "finished",
    ]
    assert api.functions and "2026-11-29" in reply["message"] and "73%" in reply["message"]


async def live_protocol_weather(runtime, prompt, tool_args, *, language):
    """Exercise the actual Live voice service, injecting the remote protocol and capturing its bound result."""
    provider = Provider()
    socket = Socket(when_ready=lambda: None)
    receipt = {}
    original_send = provider.send

    async def send_event(raw):
        await original_send(raw)
        v = json.loads(raw)
        if v["type"] == "session.start":
            session = v["session"]
            receipt.update(
                model=session["model"], delegation_model=session["delegation"]["responses"]["model"]
            )
            schema = next(
                t
                for t in session["delegation"]["responses"]["tools"]
                if t["name"] == "weather_query"
            )["parameters"]
            assert "location" in schema["required"] and "start_date" in schema["properties"]
            await provider.queue.put(
                {"type": "session.started", "session": {"model": session["model"]}}
            )
            cut = max(1, len(prompt) // 2)
            for a, b, words in [(100, 400, prompt[:cut]), (400, 780, prompt[cut:])]:
                await provider.queue.put(
                    {
                        "type": "session.input_transcript.delta",
                        "delta": words,
                        "start_ms": a,
                        "end_ms": b,
                    }
                )
            events = [
                {"type": "response.created", "response": {"id": "r_weather"}},
                {
                    "type": "response.function_call_arguments.done",
                    "response_id": "r_weather",
                    "call_id": "weather_result",
                    "name": "weather_query",
                    "arguments": json.dumps(tool_args),
                },
                {
                    "type": "response.completed",
                    "response": {
                        "id": "r_weather",
                        "output": [],
                        "usage": {"input_tokens": 5, "output_tokens": 3},
                    },
                },
            ]
            for e in events:
                await provider.queue.put(
                    {"type": "response.event", "delegation_id": "d_weather", "event": e}
                )
        elif v["type"] == "response.item.create":
            assert (
                v["item"]["type"] == "function_call_output"
                and v["item"]["call_id"] == "weather_result"
            )
            receipt["result"] = json.loads(v["item"]["output"])
            await provider.queue.put(
                {
                    "type": "session.output_transcript.delta",
                    "delta": receipt["result"]["summary"],
                    "start_ms": 950,
                    "end_ms": 1550,
                }
            )
        elif v["type"] == "session.close":
            await provider.queue.put({"type": "session.closed", "usage": {"seconds": 2}})

    provider.send = send_event
    original_client = socket.send_json

    async def client_send(event):
        await original_client(event)
        if event.get("type") == "transcript" and event.get("role") == "assistant":
            receipt["caption"] = event["text"]
            await socket.queue.put({"type": "stop"})

    socket.send_json = client_send
    runtime.voice.config = VoiceConfig(
        "openai_live",
        OPENAI_LIVE_ENDPOINT,
        "gpt-live-1.1",
        "fictional-key",
        "marin",
        backend_model="gpt-6.2-sol",
    )
    runtime.voice.connector = lambda *args, **kwargs: provider
    owner = {"kind": "owner", "id": "owner", "session": runtime.store.create_owner_session()}
    await asyncio.wait_for(
        runtime.voice.run(
            socket, runtime.voice.consume(runtime.voice.ticket(owner)["ticket"]), language
        ),
        timeout=25,
    )
    assert not [e for e in socket.messages if e["type"] == "error"]
    assert receipt["result"]["available"] and receipt["caption"] == receipt["result"]["summary"]
    return receipt


def test_gpt_live_service_binds_chunked_spoken_place_even_if_function_omits_it(tmp_path):
    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.data.weather_provider = WeatherService(fixture_weather, now=lambda: NOW)
    receipt = asyncio.run(live_protocol_weather(runtime, "帮我查一下东京的天气", {}, language="zh"))
    assert receipt["model"] == "gpt-live-1.1" and receipt["result"]["country_code"] == "JP"
    assert "73%" in receipt["caption"] and "03:00–05:00" in receipt["caption"]
    assert runtime.assistant.audit.listing(1)[0]["channel"] == "voice"


@pytest.mark.parametrize(
    "prompt",
    [
        "Compare the weather in Tokyo and Paris",
        "帮我比较东京和香港的天气",
        "What's the weather in my calendar meeting location?",
        "请看图片上的天气",
    ],
)
def test_multi_intent_or_private_context_is_not_sent_as_a_city(prompt):
    assert direct_query(prompt) is None


def test_model_call_without_destination_never_defaults_to_hong_kong(tmp_path):
    from desk.tool_policy import execute_tool

    runtime = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    runtime.data.weather_provider.fetch = lambda *_: pytest.fail(
        "A missing place must not fetch weather"
    )
    out = execute_tool(
        runtime, "weather_query", {}, "missing-city", scope="replay", channel="voice"
    )
    assert out["status"] == "missing_city" and not out["available"]


def test_city_and_coordinate_forecasts_expire_at_the_destination_midnight():
    wall = [datetime(2026, 11, 22, 14, 59, 58, tzinfo=UTC)]
    for name in ("Tokyo", "35.69,139.69"):
        wall[0] = datetime(2026, 11, 22, 14, 59, 58, tzinfo=UTC)
        forecasts = []

        def fetch(url, params):
            if "/search" in url:
                return {"results": [JAPAN]}
            forecasts.append(True)
            return model_data(params, now=wall[0])

        service = WeatherService(fetch, now=lambda: wall[0], clock=lambda: wall[0].timestamp())
        query = WeatherQuery(location=name, period="today")
        assert service.query(query)["days"][0]["date"] == "2026-11-22"
        wall[0] += timedelta(seconds=3)
        assert service.query(query)["days"][0]["date"] == "2026-11-23"
        assert len(forecasts) == 2


@pytest.mark.parametrize(("failing_name", "available"), [("东京", True), ("東京", False)])
def test_unavailable_script_variant_never_substitutes_a_village(failing_name, available):
    def fetch(url, params):
        if params.get("name") == failing_name:
            raise ValueError("Geocoding connection failed")
        return fixture_weather(url, params)

    out = WeatherService(fetch, now=lambda: NOW).query(
        WeatherQuery(location="东京", period="today")
    )
    assert out["available"] is available
    if available:
        assert out["country_code"] == "JP"
    else:
        assert out["status"] == "unavailable"
