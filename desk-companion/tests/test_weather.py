from datetime import UTC, datetime, timedelta
import pytest
from pydantic import ValidationError
from desk.weather import WeatherLocation, WeatherService


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
