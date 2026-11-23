from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest

from desk.app import create_app
from desk.weather import WeatherQuery, WeatherService
from test_global_weather import NOW, login, model_data, send

AIRPORT = {
    "id": 6300307,
    "name": "Narita International Airport",
    "latitude": 35.76472,
    "longitude": 140.38638,
    "feature_code": "AIRP",
    "country_code": "JP",
    "country": "Japan",
    "admin1": "Chiba",
    "timezone": "Asia/Tokyo",
}


@pytest.mark.parametrize(
    ("message", "place"),
    [
        ("帮我查一下成田国际机场明天的天气", "成田国际机场"),
        ("Will it rain in Narita International Airport tomorrow?", "Narita International Airport"),
        ("Will it rain in 成田国际机场 tomorrow?", "成田国际机场"),
    ],
)
def test_normal_airport_weather_uses_verified_point_day_and_rain(tmp_path, message, place):
    app = create_app(tmp_path, password="fixture", scheduler=False)
    sent = []

    def fetch(url, params):
        if "/search" in url:
            if params["name"] == "成田國際機場":
                return {}
            if params["language"] == "zh":
                return {"results": [dict(AIRPORT, name="成田国际机场")]}
            return {"results": [AIRPORT]}
        sent.append(params)
        return model_data(params)

    app.state.runtime.data.weather_provider = WeatherService(fetch, now=lambda: NOW)
    answer, _ = send(login(app), "airport", message)
    assert len(sent) == 1 and (sent[0]["latitude"], sent[0]["longitude"], sent[0]["timezone"]) == (
        35.76,
        140.39,
        "Asia/Tokyo",
    )
    tomorrow = (NOW.astimezone(ZoneInfo("Asia/Tokyo")).date() + timedelta(days=1)).isoformat()
    assert all(s in answer["message"] for s in (place, tomorrow, "73%", "03:00–05:00"))


@pytest.mark.parametrize(
    ("query", "rows", "status"),
    [
        (
            "Mount Fuji",
            [dict(AIRPORT, id=5263647, name="Mount Fuji Airport", country_code="US")],
            "not_found",
        ),
        (
            "NRT",
            [dict(AIRPORT, id=2111684, name="Narita", feature_code="PPLA2"), AIRPORT],
            "not_found",
        ),
        (
            "River Airport",
            [
                dict(AIRPORT, name="River Airport", admin1="West", population=2_000_000),
                dict(AIRPORT, id=2, name="River Airport", admin1="East"),
            ],
            "ambiguous",
        ),
        (
            "River Airport",
            [
                dict(AIRPORT, name="River Airport"),
                dict(AIRPORT, id=2, name="River Airport", feature_code="PPL", population=2_000_000),
            ],
            "ambiguous",
        ),
        ("Japan", [dict(AIRPORT, name="Japan", feature_code="PCLI")], "specify_city"),
        (
            "Example Range",
            [
                dict(AIRPORT, name="Example Range", feature_code="MTS"),
                dict(AIRPORT, id=2, name="Example Range Village", feature_code="PPL"),
            ],
            "not_found",
        ),
        ("成田国际", [dict(AIRPORT, name="成田国际机场")], "not_found"),
    ],
)
def test_fuzzy_different_site_ambiguity_and_large_features_never_request_weather(
    query, rows, status
):
    def fetch(url, params):
        assert "/search" in url
        return {"results": rows}

    out = WeatherService(fetch, now=lambda: NOW).query(WeatherQuery(location=query, period="today"))
    assert out["status"] == status and not out["available"] and "coordinates" in out["summary"]
    if status == "ambiguous":
        assert len(set(out["choices"])) == 2


def test_verified_mountain_name_has_the_same_fixed_point_rule_as_an_airport():
    calls = []

    def source(url, params):
        if "/search" in url:
            return {
                "results": [
                    dict(
                        AIRPORT,
                        name="Example Peak",
                        feature_code="PK",
                        latitude=35.11,
                        longitude=138.7,
                    )
                ]
            }
        calls.append(params)
        return model_data(params)

    out = WeatherService(source, now=lambda: NOW).query(
        WeatherQuery(location="Example Peak", period="today")
    )
    assert out["available"] and out["place"] == "Example Peak"
    assert (calls[0]["latitude"], calls[0]["longitude"]) == (35.11, 138.7)
