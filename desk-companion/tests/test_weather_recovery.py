import json

import httpx
import pytest

from desk.app import create_app
from desk.weather import WeatherQuery, WeatherService, read_weather_json
from test_global_weather import NOW, fixture_weather, login, model_data, send


@pytest.mark.parametrize("failure", ["read_timeout", "disconnected", "bad_gateway"])
def test_first_normal_request_recovers_a_transient_forecast_read(tmp_path, failure):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    runtime.data.weather_provider.now = lambda: NOW
    tries = []

    def upstream(request):
        params = dict(request.url.params)
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json=fixture_weather(str(request.url), params))
        tries.append(request.extensions["timeout"]["connect"])
        if len(tries) == 1:
            if failure == "read_timeout":
                raise httpx.ReadTimeout("cold response", request=request)
            if failure == "disconnected":
                raise httpx.RemoteProtocolError("peer closed before headers", request=request)
            return httpx.Response(502)
        params["forecast_days"] = int(params["forecast_days"])
        return httpx.Response(200, json=model_data(params))

    runtime.data.transport = httpx.MockTransport(upstream)
    answer, _ = send(login(app), "first", "帮我查一下东京的天气")
    assert tries == [3.0, 6.0]
    assert all(s in answer["message"] for s in ("东京", "2026-11-23", "9.5°C", "73%"))


@pytest.mark.parametrize(
    ("fault", "reason", "max_requests", "backoff"),
    [
        ("network", "timeout", 2, 5),
        ("rate_limit", "http_status", 1, 90),
        ("server_backoff", "http_status", 1, 90),
        ("not_authorized", "http_status", 1, 45),
        ("invalid", "invalid_data", 1, 45),
    ],
)
def test_failed_source_is_identifiable_and_backoff_respects_the_server(
    fault, reason, max_requests, backoff
):
    calls = []
    clock = [0.0]

    def upstream(req):
        calls.append(req.url)
        if fault == "network":
            raise httpx.ReadTimeout("do not persist a request URL", request=req)
        if fault == "invalid":
            return httpx.Response(200, content=b"bad json")
        if fault == "not_authorized":
            return httpx.Response(403)
        return httpx.Response(429 if fault == "rate_limit" else 503, headers={"Retry-After": "90"})

    def fetch(url, params):
        return read_weather_json(url, params, transport=httpx.MockTransport(upstream))

    svc = WeatherService(fetch, now=lambda: NOW, clock=lambda: clock[0])
    query = WeatherQuery(location="Córdoba", period="today")
    first = svc.query(query)
    assert (
        first["source_failure"]["stage"] == "geocoding"
        and first["source_failure"]["reason"] == reason
    )
    assert not first["available"] and len(calls) == max_requests
    assert "Córdoba" not in json.dumps(first["source_failure"], ensure_ascii=False)
    clock[0] = backoff - 0.1
    assert (
        svc.query(query)["source_failure"] == first["source_failure"] and len(calls) == max_requests
    )
    clock[0] = backoff + 0.1
    assert not svc.query(query)["available"] and len(calls) == 2 * max_requests


def test_a_forecast_outage_never_returns_hong_kong_or_invents_precipitation():
    def fetch(url, params):
        if "/search" in url:
            return fixture_weather(url, params)
        raise httpx.ReadTimeout("temporary outage")

    out = WeatherService(fetch, now=lambda: NOW).query(
        WeatherQuery(location="Tokyo", period="today")
    )
    assert out["source_failure"] == {"stage": "global_forecast", "reason": "timeout"}
    assert not out["available"] and not out["days"] and "Hong Kong" not in out["summary"]


def test_ordinary_failure_receipt_keeps_its_stage_when_the_provider_recovers(tmp_path):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    runtime = app.state.runtime
    clock = [0.0]
    online = [False]

    def fetch(url, params):
        if "/search" in url or online[0]:
            return fixture_weather(url, params)
        raise httpx.ReadTimeout("private URL must never enter the receipt")

    runtime.data.weather_provider = WeatherService(fetch, now=lambda: NOW, clock=lambda: clock[0])
    client = login(app)
    original, _ = send(client, "original", "帮我查一下东京的天气")
    assert original["weather_source_failure"] == {"stage": "global_forecast", "reason": "timeout"}
    clock[0] = 5.1
    online[0] = True
    again, _ = send(client, "original", "帮我查一下东京的天气")
    assert (
        again["message"] == original["message"]
        and again["weather_source_failure"] == original["weather_source_failure"]
    )
    recovered, _ = send(client, "fresh", "帮我查一下东京的天气")
    assert "9.5°C" in recovered["message"] and "weather_source_failure" not in recovered


@pytest.mark.parametrize(
    ("lang", "prompt", "missing"),
    [
        ("zh", "帮我看一下香港的天气", "暂时查不到今天的降雨预报。"),
        ("en", "Will it rain in Hong Kong today?", "Today's rain forecast is unavailable."),
    ],
)
def test_normal_today_names_a_forecast_outage_while_current_only_stays_short(
    tmp_path, lang, prompt, missing
):
    app = create_app(tmp_path, password="fixture", scheduler=False)

    def fetch(url, params):
        if params.get("dataType") == "rhrread":
            return {
                "temperature": {
                    "recordTime": NOW.isoformat(),
                    "data": [{"place": "Hong Kong Observatory", "unit": "C", "value": 24}],
                }
            }
        raise httpx.ConnectError("forecast feed offline")

    weather = WeatherService(fetch, now=lambda: NOW)
    app.state.runtime.data.weather_provider = weather
    client = login(app)
    reply, _ = send(client, "only-station", prompt)
    assert "24°C" in reply["message"] and reply["message"].count(missing) == 1
    current = weather.query(WeatherQuery(location="Hong Kong", period="current", language=lang))
    assert "24°C" in current["summary"] and missing not in current["summary"]


@pytest.mark.parametrize(
    ("day", "bulletin", "phrase", "missing"),
    [
        ({"peak_precipitation_probability_pct": 0}, None, "0%", False),
        ({"precipitation_mm": 0}, None, "0 mm", False),
        ({"significant_rain_category": "Low"}, None, "low chance", False),
        ({"conditions": "A few showers tonight"}, None, "A few showers tonight", False),
        (
            {},
            {"period": "Weather forecast for tonight", "conditions": "A few showers tonight."},
            "A few showers tonight.",
            False,
        ),
        ({"minimum_c": 21, "maximum_c": 24}, None, "21 to 24°C", True),
    ],
)
def test_only_missing_forecast_evidence_needs_the_short_rain_notice(day, bulletin, phrase, missing):
    from desk.weather_reply import weather_summary

    today = "2026-11-23"
    result = {
        "available": True,
        "area": "hong_kong",
        "place": "Hong Kong",
        "source": "Hong Kong Observatory",
        "period": "today",
        "requested_days": 1,
        "local_date": today,
        "current": {"time": "2026-11-23T21:00:00+08:00", "temperature_c": 24, "basis": "station"},
        "days": [{"date": today, **day}] if day else [],
        "local_forecast": bulletin,
    }
    summary = weather_summary(result, "en")
    assert phrase in summary and ("rain forecast is unavailable" in summary) == missing


def test_hko_recorded_bulletin_answers_rain_when_numeric_forecasts_are_offline(tmp_path):
    from datetime import datetime

    app = create_app(tmp_path, password="fixture", scheduler=False)

    def official(url, params):
        if params.get("dataType") == "rhrread":
            return {
                "temperature": {
                    "recordTime": "2026-11-23T21:00:00+08:00",
                    "data": [{"place": "Hong Kong Observatory", "value": 23, "unit": "C"}],
                }
            }
        if params.get("dataType") == "flw":
            # The Observatory's 20:45 short forecast, captured in the 23 November public acceptance.
            return {
                "updateTime": "2026-11-23T20:45:00+08:00",
                "forecastPeriod": "本港地区今晚及明日天气预测",
                "forecastDesc": "多云，有几阵雨。明日初时雨势较为频密。",
            }
        raise httpx.ReadTimeout("numeric forecast offline")

    app.state.runtime.data.weather_provider = WeatherService(
        official, now=lambda: datetime.fromisoformat("2026-11-23T21:20:00+08:00")
    )
    reply, _ = send(login(app), "hko-qualitative", "帮我看一下香港的天气")
    assert "23°C" in reply["message"] and "有几阵雨" in reply["message"]
    assert "暂时查不到" not in reply["message"] and "%" not in reply["message"]
