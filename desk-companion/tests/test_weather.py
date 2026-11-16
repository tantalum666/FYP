from datetime import UTC, datetime, timedelta
import pytest
from pydantic import ValidationError
from desk.weather import WeatherLocation, WeatherService
from desk.weather import WeatherQuery


def test_coarse_location_only_and_cached_observation():
    calls = []

    def fetch(url, params):
        calls.append((url, params))
        return {
            "current": {
                "temperature_2m": 23.5,
                "time": datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            }
        }

    service = WeatherService(fetch=fetch)
    location = WeatherLocation(latitude=22.31973, longitude=114.17042)
    first = service.current(location)
    assert first["temperature"] == 23.5 and first["area"] == "nearby"
    assert calls[0][1]["latitude"] == 22.3 and calls[0][1]["longitude"] == 114.2
    assert service.current(location) == first and len(calls) == 1
    assert "latitude" not in first and "longitude" not in first


def test_old_observation_and_bad_coordinates_are_not_current_weather():
    def fetch(*_):
        return {
            "temperature": {
                "recordTime": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "data": [{"place": "Hong Kong Observatory", "unit": "C", "value": 24}],
            }
        }

    assert WeatherService(fetch=fetch).current() == {"available": False, "area": "hong_kong"}
    with pytest.raises(ValidationError):
        WeatherLocation(latitude=float("nan"), longitude=114)
    with pytest.raises(ValidationError):
        WeatherLocation(latitude=91, longitude=114)


def test_home_and_existing_weather_settings_share_cache_and_respect_opt_out(tmp_path):
    from desk.app import create_app
    from desk.workspace_data import PreferencesUpdate, WorkspacePreferences

    runtime = create_app(tmp_path, password="fictional", scheduler=False).state.runtime
    seen = []

    def fetch(url, params):
        seen.append((url, params))
        return {
            "temperature": {
                "recordTime": datetime.now(UTC).isoformat(),
                "data": [{"place": "Hong Kong Observatory", "value": 26, "unit": "C"}],
            }
        }

    runtime.data.weather_provider.fetch = fetch
    assert not runtime.data.read_weather()["available"] and not seen
    runtime.data.update(
        PreferencesUpdate(
            expected_version=1, preferences=WorkspacePreferences(weather_location="hong_kong")
        ),
        "choose-hk",
    )
    runtime.data.poll_weather()
    assert runtime.data.read_weather()["temperature"] == 26 and len(seen) == 1
    assert runtime.data.snapshot()["weather"]["temperature_c"] == 26
    runtime.data.update(
        PreferencesUpdate(
            expected_version=2, preferences=WorkspacePreferences(weather_location="none")
        ),
        "disable-weather",
    )
    assert not runtime.data.read_weather()["available"] and len(seen) == 1
    assert runtime.data.snapshot()["weather"]["status"] == "not_configured"


def forecast_fixture(now):
    return {
        "updateTime": now.isoformat(),
        "generalSituation": "Cooler later in the week.",
        "weatherForecast": [
            {
                "forecastDate": (now + timedelta(days=i)).strftime("%Y%m%d"),
                "forecastMintemp": {"value": 18, "unit": "C"},
                "forecastMaxtemp": {"value": 24, "unit": "C"},
                "forecastWeather": "Cloudy",
                "forecastWind": "Easterly winds",
                "PSR": "Low",
            }
            for i in range(1, 10)
        ],
    }


def test_forecast_tool_reads_dated_hko_data_without_enabling_location(tmp_path):
    from desk.app import create_app
    from desk.tool_policy import execute_tool

    r = create_app(tmp_path, password="fixture", scheduler=False).state.runtime
    calls = []

    def fetch(url, params):
        calls.append((url, params))
        return forecast_fixture(r.store.clock())

    r.data.weather_provider.fetch = fetch
    result = execute_tool(
        r, "weather_query", {"days": 7, "language": "zh"}, "forecast", scope="test", channel="voice"
    )
    assert result["available"] and len(result["days"]) == 7
    assert result["source"] == "Hong Kong Observatory"
    assert result["days"][0]["significant_rain_category"] == "Low"
    assert calls[0][1] == {"dataType": "fnd", "lang": "sc"}
    assert r.data.preferences()["weather_location"] == "none"
    assert (
        r.data.weather_provider.query(WeatherQuery(days=3, language="zh"))["days"]
        == result["days"][:3]
    )
    assert len(calls) == 1


@pytest.mark.parametrize("fault", ["stale", "bad_temperature", "duplicate"])
def test_forecast_does_not_label_stale_or_invalid_data_as_a_current_result(fault):
    now = datetime.now(UTC)
    data = forecast_fixture(now)
    if fault == "stale":
        data["updateTime"] = (now - timedelta(days=2)).isoformat()
    elif fault == "bad_temperature":
        data["weatherForecast"][0]["forecastMintemp"]["value"] = float("nan")
    else:
        data["weatherForecast"][1]["forecastDate"] = data["weatherForecast"][0]["forecastDate"]
    result = WeatherService(fetch=lambda *_: data, now=lambda: now).query(WeatherQuery())
    assert result["available"] is False and result["days"] == []
