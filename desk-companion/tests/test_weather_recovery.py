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
