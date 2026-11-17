"""Public weather reads using coarse coordinates; no location persistence or model calls."""

from datetime import UTC, datetime
import json
import math
import threading
import time
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
import httpx
from pydantic import Field

from .schemas import StrictModel


class WeatherLocation(StrictModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class WeatherQuery(StrictModel):
    location: Literal["hong_kong"] = "hong_kong"
    period: Literal["current", "forecast"] = "forecast"
    days: int = Field(default=7, ge=1, le=9, strict=True)
    language: Literal["en", "zh"] = "en"


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
        self.forecasts = {}
        self.lock = threading.Lock()

    def query(self, query: WeatherQuery):
        # An explicit city request does not enable persistent location tracking
        # or change the home-widget preference.
        if query.period == "current":
            return self.current()
        with self.lock:
            now = self.now()
            today = now.astimezone(ZoneInfo("Asia/Hong_Kong")).date()
            key = (query.language, today.isoformat())
            cached = self.forecasts.get(key)
            if cached and self.clock() < cached[0]:
                result = cached[1]
            else:
                result = {"available": False, "area": "hong_kong", "period": "forecast"}
                try:
                    data = self.fetch(
                        "https://data.weather.gov.hk/weatherAPI/opendata/weather.php",
                        {"dataType": "fnd", "lang": "sc" if query.language == "zh" else "en"},
                    )
                    issued = datetime.fromisoformat(data["updateTime"])
                    if issued.tzinfo is None or not -300 <= (now - issued).total_seconds() <= 86400:
                        raise ValueError("Forecast issue time is stale")
                    days = []
                    for row in data["weatherForecast"][:9]:
                        day = datetime.strptime(row["forecastDate"], "%Y%m%d").date()
                        if not 0 <= (day - today).days <= 9:
                            continue
                        low, high = row["forecastMintemp"], row["forecastMaxtemp"]
                        if (
                            any(
                                x.get("unit") != "C"
                                or type(x.get("value")) not in (int, float)
                                or not math.isfinite(x["value"])
                                or not -50 <= x["value"] <= 65
                                for x in (low, high)
                            )
                            or low["value"] > high["value"]
                        ):
                            raise ValueError("Invalid forecast temperature")
                        days.append(
                            {
                                "date": day.isoformat(),
                                "minimum_c": low["value"],
                                "maximum_c": high["value"],
                                "conditions": str(row["forecastWeather"])[:800],
                                "wind": str(row.get("forecastWind", ""))[:400],
                                # HKO supplies a category, not a numeric percentage.
                                "significant_rain_category": str(row.get("PSR", ""))[:60],
                            }
                        )
                    if not days or len({d["date"] for d in days}) != len(days):
                        raise ValueError("Missing or duplicate forecast dates")
                    result.update(
                        available=True,
                        issued_at=issued.isoformat(),
                        timezone="Asia/Hong_Kong",
                        source="Hong Kong Observatory",
                        source_url="https://www.hko.gov.hk/en/wxinfo/currwx/fnd.htm",
                        general_situation=str(data.get("generalSituation", ""))[:1600],
                        days=sorted(days, key=lambda d: d["date"]),
                    )
                except (httpx.HTTPError, ValueError, TypeError, KeyError):
                    pass
                # Keep only today's two language snapshots, including bounded failures.
                self.forecasts = {k: v for k, v in self.forecasts.items() if k[1] == key[1]}
                self.forecasts[key] = (self.clock() + (900 if result["available"] else 60), result)
            return {
                **result,
                "requested_days": query.days,
                "days": result.get("days", [])[: query.days],
            }

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

    @router.post("/query")
    def query(payload: WeatherQuery):
        return data.weather_provider.query(payload)

    return router
