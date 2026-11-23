"""Shared public weather reads. Explicit destinations never change the Home preference."""

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
import json
import threading
import time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
import httpx
from pydantic import Field, field_validator

from .schemas import StrictModel
from .weather_forecast import OPEN_METEO_URL, StaleWeather, fresh_timestamp, number, world_forecast
from .weather_places import HONG_KONG, PlaceProblem, resolve_place, simplified
from .weather_reply import weather_summary

HKO_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
HKO = "Hong Kong Observatory"
HKO_READS = ThreadPoolExecutor(max_workers=6, thread_name_prefix="weather-hk")
WEATHER_TOOL_DESCRIPTION = (
    "Look up current weather, today's local outlook or dates up to nine days at a time in cities worldwide. "
    "Pass the user's city, and country/region qualifier when given. For a normal weather or rain question "
    "use period=today. Resolve tomorrow/day_after_tomorrow in the destination's timezone. For a requested "
    "week use forecast and days=7. Use the returned summary, observed/model time, daily temperatures, "
    "precipitation windows/probability or official qualitative forecast. Ask which city for an ambiguous "
    "place. Never substitute a different city, infer location permission, or convert past rainfall into odds."
)
DATA_ERRORS = (
    httpx.HTTPError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    OverflowError,
    StopIteration,
    ZoneInfoNotFoundError,
)


class WeatherLocation(StrictModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class WeatherQuery(StrictModel):
    location: str = Field(
        default="hong_kong",
        min_length=1,
        max_length=120,
        description="Explicit city name in any script, optionally followed by a comma and country/region, or explicit latitude,longitude. Ask if the destination is missing.",
    )
    country_code: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z]{2}$",
        description="Optional ISO two-letter country filter.",
    )
    period: Literal["current", "today", "forecast"] = "forecast"
    days: int = Field(default=7, ge=1, le=9, strict=True)
    start_date: date | Literal["today", "tomorrow", "day_after_tomorrow"] | None = Field(
        default=None,
        description="First requested date (YYYY-MM-DD) or a relative day in the destination.",
    )
    language: Literal["en", "zh"] = "en"

    @field_validator("location")
    @classmethod
    def public_place(cls, value):
        value = value.strip()
        if not value or any(not char.isprintable() for char in value):
            raise ValueError("A public place name is required")
        return value

    @field_validator("country_code")
    @classmethod
    def uppercase_code(cls, value):
        return value.upper() if value else None

    def first_day(self, today):
        if isinstance(self.start_date, date):
            return self.start_date
        return today + timedelta(
            days={"tomorrow": 1, "day_after_tomorrow": 2}.get(self.start_date, 0)
        )

    @property
    def current_day(self):
        if self.start_date is not None:
            return self.start_date == "today"
        return self.period != "forecast" or (
            "location" in self.model_fields_set and not {"days", "period"} & self.model_fields_set
        )

    @property
    def count(self):
        if self.current_day and self.start_date is None:
            return 1
        return (
            1 if self.start_date is not None and "days" not in self.model_fields_set else self.days
        )


def weather_tool_schema():
    # The deployed API also accepts older HK-only requests. New model calls must name the place.
    return {**WeatherQuery.model_json_schema(), "required": ["location", "period", "language"]}


RETRYABLE_STATUS = {408, 500, 502, 503, 504}
TRANSIENT_NETWORK = (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)


class WeatherReadFailure(ValueError):
    def __init__(self, detail):
        super().__init__(detail["reason"])
        self.detail = detail


def read_failure(error, now):
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        backoff = 5 if status in RETRYABLE_STATUS else 45
        retry = error.response.headers.get("Retry-After")
        if retry:
            try:
                seconds = (
                    int(retry)
                    if retry.isdecimal()
                    else (parsedate_to_datetime(retry) - now).total_seconds()
                )
                backoff = max(backoff, min(86400, seconds))
            except (TypeError, ValueError, OverflowError):
                pass
        return {"reason": "http_status", "http_status": status}, backoff
    if isinstance(error, TRANSIENT_NETWORK):
        return {
            "reason": "timeout" if isinstance(error, httpx.TimeoutException) else "connection"
        }, 5
    return {"reason": "invalid_data"}, 45


def read_weather_json(url, params, *, transport=None):
    # Fast first connection, one longer cold TLS retry for an idempotent public GET.
    connect_limits = (7.0, 7.0) if url == HKO_URL else (3.0, 6.0)
    with httpx.Client(follow_redirects=False, trust_env=False, transport=transport) as client:
        for index, connect in enumerate(connect_limits):
            try:
                with client.stream(
                    "GET", url, params=params, timeout=httpx.Timeout(4.0, connect=connect)
                ) as response:
                    if (
                        index == 0
                        and response.status_code in RETRYABLE_STATUS
                        and "Retry-After" not in response.headers
                    ):
                        continue
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if len(body) + len(chunk) > 65536:
                            raise ValueError("Weather response too large")
                        body.extend(chunk)
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise ValueError("Invalid public weather response")
                return result
            except TRANSIENT_NETWORK:
                if index:
                    raise


class WeatherService:
    def __init__(
        self, fetch=read_weather_json, clock=time.monotonic, now=lambda: datetime.now(UTC)
    ):
        self.fetch, self.clock, self.now = fetch, clock, now
        self.cache = OrderedDict()
        self.pending = {}
        self.lock = threading.Lock()

    def _cache_lifetime(self, data, params, ttl):
        if not isinstance(data, dict):
            return 45
        zone = data.get("timezone") if "daily" in params else None
        if params.get("dataType") in {"flw", "fnd"}:
            zone = HONG_KONG.timezone
        if not zone:
            return ttl
        try:
            now = self.now().astimezone(ZoneInfo(zone))
            midnight = datetime.combine(
                now.date() + timedelta(days=1), datetime.min.time(), tzinfo=now.tzinfo
            )
            return min(ttl, max(0, midnight.timestamp() - now.timestamp()))
        except (ValueError, KeyError, TypeError):
            return 45

    def _read(self, url, params, *, ttl=600):
        key = (url, tuple(sorted(params.items())))
        with self.lock:
            cached = self.cache.get(key)
            if cached and self.clock() < cached[0]:
                self.cache.move_to_end(key)
                if cached[2]:
                    raise WeatherReadFailure(cached[2])
                return cached[1]
            future = self.pending.get(key)
            leader = future is None
            if leader:
                if len(self.pending) >= 12:
                    raise WeatherReadFailure({"reason": "busy"})
                self.pending[key] = future = Future()
        if not leader:
            try:
                return future.result(timeout=16 if url == HKO_URL else 12)
            except TimeoutError as exc:
                raise WeatherReadFailure({"reason": "timeout"}) from exc
        data, failure, lifetime = None, None, 0
        try:
            data = self.fetch(url, params)
            lifetime = self._cache_lifetime(data, params, ttl)
            future.set_result(data)
            return data
        except DATA_ERRORS as error:
            failure, lifetime = read_failure(error, self.now())
            failed = WeatherReadFailure(failure)
            future.set_exception(failed)
            raise failed from None
        except Exception as error:
            future.set_exception(error)
            raise
        finally:
            with self.lock:
                if len(self.cache) >= 64 and key not in self.cache:
                    self.cache.popitem(last=False)
                self.cache[key] = (self.clock() + lifetime, data, failure)
                self.pending.pop(key)

    def _hko(self, data_type, language):
        return self._read(
            HKO_URL, {"dataType": data_type, "lang": "sc" if language == "zh" else "en"}
        )

    def _hko_current(self, now):
        data = self._hko("rhrread", "en")["temperature"]
        stamp = fresh_timestamp(data["recordTime"], now, 7200).astimezone(
            ZoneInfo(HONG_KONG.timezone)
        )
        temp = next(
            row["value"]
            for row in data["data"]
            if row["place"] == "Hong Kong Observatory" and row.get("unit", "C") == "C"
        )
        return {
            "time": stamp.isoformat(),
            "temperature_c": number(temp, -70, 65),
            "basis": "station",
        }

    def _hko_days(self, language, now, today):
        data = self._hko("fnd", language)
        issued = fresh_timestamp(data["updateTime"], now, 86400)
        days = []
        for row in data["weatherForecast"][:9]:
            day = datetime.strptime(row["forecastDate"], "%Y%m%d").date()
            if not 0 <= (day - today).days <= 9:
                continue
            low, high = row["forecastMintemp"], row["forecastMaxtemp"]
            if low["unit"] != "C" or high["unit"] != "C":
                raise ValueError("Invalid HKO temperature units")
            minimum, maximum = number(low["value"], -50, 65), number(high["value"], -50, 65)
            if minimum > maximum:
                raise ValueError("Invalid HKO temperature range")
            days.append(
                {
                    "date": day.isoformat(),
                    "minimum_c": minimum,
                    "maximum_c": maximum,
                    "conditions": str(row["forecastWeather"])[:800],
                    "wind": str(row.get("forecastWind", ""))[:400],
                    "significant_rain_category": str(row.get("PSR", ""))[:60],
                }
            )
        if not days or len({d["date"] for d in days}) != len(days):
            raise ValueError("Missing or duplicate HKO forecast dates")
        return {
            "issued_at": issued.isoformat(),
            "general_situation": str(data.get("generalSituation", ""))[:1600],
            "days": sorted(days, key=lambda d: d["date"]),
        }

    def _hko_outlook(self, language, now):
        local = self._hko("flw", language)
        issued = fresh_timestamp(local["updateTime"], now, 86400)
        zone = ZoneInfo(HONG_KONG.timezone)
        if issued.astimezone(zone).date() != now.astimezone(zone).date():
            raise StaleWeather(issued)
        if not (local.get("forecastPeriod") and local.get("forecastDesc")):
            raise ValueError("Missing HKO local outlook")
        return {
            "period": local["forecastPeriod"][:200],
            "conditions": local["forecastDesc"][:800],
            "issued_at": issued.isoformat(),
            "source": HKO,
            "source_url": "https://www.hko.gov.hk/en/wxinfo/currwx/flw.htm",
        }

    def _hong_kong(self, query, now):
        zone = ZoneInfo(HONG_KONG.timezone)
        today = now.astimezone(zone).date()
        first = query.first_day(today)
        result = {
            "area": "hong_kong",
            "place": "香港" if query.language == "zh" else "Hong Kong",
            "timezone": zone.key,
            "source": HKO,
            "source_url": "https://www.hko.gov.hk/en/wxinfo/currwx/fnd.htm",
            "local_date": today.isoformat(),
            "days": [],
        }
        if first < today or first > today + timedelta(days=9):
            return {**result, "status": "out_of_range"}
        include_today = first == today and (query.current_day or query.start_date is not None)
        # The station observation and the official local/daily forecasts are independent.
        reads = {}
        if include_today:
            reads = {
                "current": HKO_READS.submit(self._hko_current, now),
                "local_forecast": HKO_READS.submit(self._hko_outlook, query.language, now),
            }
        try:
            result.update(self._hko_days(query.language, now, today))
        except StaleWeather as error:
            result["last_report_at"] = error.stamp
        except DATA_ERRORS:
            pass
        if include_today and not any(row["date"] == today.isoformat() for row in result["days"]):
            # A model can supply today's absent numerical forecast, but must never replace the station.
            try:
                model = world_forecast(self._read, HONG_KONG, query.language, now, 1)
                result["days"][:0] = [{**row, "source": "Open-Meteo"} for row in model["days"]]
            except DATA_ERRORS:
                pass
        for key, future in reads.items():
            try:
                result[key] = future.result()
            except StaleWeather as error:
                result["last_report_at"] = error.stamp
            except DATA_ERRORS:
                pass
        if current := result.get("current"):
            result.update(temperature=current["temperature_c"], observed_at=current["time"])
        if query.start_date is not None or include_today:
            last = first + timedelta(days=query.count)
            result["days"] = [
                d for d in result["days"] if first.isoformat() <= d["date"] < last.isoformat()
            ]
        result["days"] = result["days"][: query.count]
        if (
            not (result.get("current") or result.get("local_forecast"))
            and result["days"]
            and all(row.get("source") == "Open-Meteo" for row in result["days"])
        ):
            result.update(source="Open-Meteo", source_url="https://open-meteo.com/en/docs")
        return result

    def _world(self, query, place, now):
        # A named city carries its IANA zone. For explicit coordinates Open-Meteo
        # resolves the zone; allow one extra day on absolute-date lookups across midnight.
        today = now.astimezone(ZoneInfo(place.timezone) if place.timezone else UTC).date()
        offset = (query.first_day(today) - today).days
        horizon = max(
            1,
            min(
                16,
                query.count
                + offset
                + int(not place.timezone and isinstance(query.start_date, date)),
            ),
        )
        info = world_forecast(self._read, place, query.language, now, horizon)
        today = now.astimezone(ZoneInfo(info["timezone"])).date()
        name = simplified(place.name) if query.language == "zh" else place.name
        result = {
            **info,
            "area": "destination",
            "place": name,
            "country": place.country,
            "region": place.region,
            "country_code": place.code,
            "local_date": today.isoformat(),
        }
        first = query.first_day(today)
        if first != today:
            result.pop("current", None)
        result["days"] = [
            d
            for d in info["days"]
            if first.isoformat() <= d["date"] < (first + timedelta(days=query.count)).isoformat()
        ]
        if first < today or first >= today + timedelta(days=16):
            result["status"] = "out_of_range"
        return result

    def query(self, query: WeatherQuery):
        result = {
            "available": False,
            "period": query.period,
            "requested_days": query.count,
            "place": query.location,
            "days": [],
        }
        stage = "geocoding"
        try:
            if "location" not in query.model_fields_set and (
                query.period == "today" or query.start_date
            ):
                raise PlaceProblem("missing_city")
            place = resolve_place(self._read, query.location, query.country_code, query.language)
            now = self.now()
            stage = "hong_kong_weather" if place == HONG_KONG else "global_forecast"
            result.update(
                self._hong_kong(query, now)
                if place == HONG_KONG
                else self._world(query, place, now)
            )
            result["available"] = bool(
                result.get("current") or result.get("local_forecast") or result["days"]
            )
        except PlaceProblem as error:
            result.update(status=error.reason, choices=error.choices)
        except StaleWeather as error:
            result.update(last_report_at=error.stamp)
        except WeatherReadFailure as error:
            result["source_failure"] = {"stage": stage, **error.detail}
        except DATA_ERRORS:
            result["source_failure"] = {"stage": stage, "reason": "invalid_data"}
        if not result["available"] and "status" not in result:
            result["status"] = "stale" if result.get("last_report_at") else "unavailable"
        if result["available"] and query.current_day and "current" not in result:
            result["current_unavailable"] = True
        if result["available"] and query.count > 1:
            covered = {d["date"] for d in result["days"]}
            if result.get("local_forecast"):
                covered.add(result["local_date"])
            if len(covered) < query.count:
                result["uncovered_days"] = query.count - len(covered)
        result["summary"] = weather_summary(result, query.language)
        return result

    def current(self, location=None):
        # The Home widget keeps its small current-only contract and preference gate.
        area = "hong_kong" if location is None else "nearby"
        try:
            if location is None:
                current = self._hko_current(self.now())
                temperature, observed, source = current["temperature_c"], current["time"], HKO
            else:
                data = self._read(
                    OPEN_METEO_URL,
                    {
                        "latitude": round(location.latitude, 1),
                        "longitude": round(location.longitude, 1),
                        "current": "temperature_2m,weather_code",
                        "timezone": "UTC",
                    },
                )
                temperature = number(data["current"]["temperature_2m"], -70, 65)
                observed = fresh_timestamp(
                    data["current"]["time"], self.now(), 7200, UTC
                ).isoformat()
                source = "Open-Meteo"
            return {
                "available": True,
                "area": area,
                "temperature": temperature,
                "observed_at": observed,
                "source": source,
            }
        except DATA_ERRORS:
            return {"available": False, "area": area}


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
