"""Public weather reads using coarse coordinates; no location persistence or model calls."""

from datetime import UTC, datetime
import json
import math
import threading
import time

from fastapi import APIRouter, Depends
import httpx
from pydantic import Field

from .schemas import StrictModel


class WeatherLocation(StrictModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


def read_weather_json(url, params, *, transport=None):
    with httpx.Client(
        timeout=5, follow_redirects=False, trust_env=False, transport=transport
    ) as client:
        with client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 65536:
                    raise ValueError("Weather response too large")
    return json.loads(body)


class WeatherService:
    def __init__(
        self, fetch=read_weather_json, clock=time.monotonic, now=lambda: datetime.now(UTC)
    ):
        self.fetch, self.clock, self.now = fetch, clock, now
        self.cache = {}
        self.lock = threading.Lock()

    def current(self, location=None):
        key = (
            None
            if location is None
            else (round(location.latitude, 1), round(location.longitude, 1))
        )
        with self.lock:
            cached = self.cache.get(key)
            if cached and self.clock() < cached[0]:
                return cached[1]
            result = {"available": False, "area": "hong_kong" if key is None else "nearby"}
            try:
                if key is None:
                    data = self.fetch(
                        "https://data.weather.gov.hk/weatherAPI/opendata/weather.php",
                        {"dataType": "rhrread", "lang": "en"},
                    )
                    temperature = next(
                        x["value"]
                        for x in data["temperature"]["data"]
                        if x["place"] == "Hong Kong Observatory" and x.get("unit", "C") == "C"
                    )
                    observed = data["temperature"]["recordTime"]
                    source = "Hong Kong Observatory"
                else:
                    data = self.fetch(
                        "https://api.open-meteo.com/v1/forecast",
                        {
                            "latitude": key[0],
                            "longitude": key[1],
                            "current": "temperature_2m,weather_code",
                            "timezone": "UTC",
                        },
                    )
                    temperature = data["current"]["temperature_2m"]
                    observed = data["current"]["time"] + "+00:00"
                    source = "Open-Meteo"
                at = datetime.fromisoformat(observed)
                if at.tzinfo is None or not -300 <= (self.now() - at).total_seconds() <= 7200:
                    raise ValueError("Weather observation is not current")
                if (
                    type(temperature) not in (int, float)
                    or not math.isfinite(temperature)
                    or not -70 <= temperature <= 65
                ):
                    raise ValueError("Invalid temperature")
                result.update(
                    available=True, temperature=temperature, observed_at=observed, source=source
                )
            except (httpx.HTTPError, ValueError, TypeError, KeyError, StopIteration):
                pass
            if len(self.cache) >= 16:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = (self.clock() + (600 if result["available"] else 60), result)
            return result


def weather_routes(data, authenticated):
    router = APIRouter(prefix="/api/weather", dependencies=[Depends(authenticated)])

    @router.get("")
    def hong_kong():
        return data.read_weather()

    @router.post("")
    def nearby(location: WeatherLocation):
        return data.read_weather(location)

    return router
