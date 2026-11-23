"""Destination-local, unit-checked Open-Meteo forecast data."""

from datetime import UTC, datetime, timedelta
import math
from zoneinfo import ZoneInfo

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DAILY = {
    "temperature_2m_min": "°C",
    "temperature_2m_max": "°C",
    "weather_code": "wmo code",
    "precipitation_probability_max": "%",
    "precipitation_sum": "mm",
}
HOURLY = {"precipitation_probability": "%", "precipitation": "mm"}
WMO = {
    0: ("clear", "晴"),
    1: ("mainly clear", "大致晴朗"),
    2: ("partly cloudy", "局部多云"),
    3: ("overcast", "阴天"),
    45: ("fog", "有雾"),
    48: ("rime fog", "有雾凇"),
    51: ("light drizzle", "毛毛雨"),
    53: ("drizzle", "毛毛雨"),
    55: ("heavy drizzle", "较强毛毛雨"),
    56: ("light freezing drizzle", "轻微冻毛毛雨"),
    57: ("freezing drizzle", "冻毛毛雨"),
    61: ("light rain", "小雨"),
    63: ("moderate rain", "中雨"),
    65: ("heavy rain", "大雨"),
    66: ("light freezing rain", "小冻雨"),
    67: ("freezing rain", "冻雨"),
    71: ("light snow", "小雪"),
    73: ("moderate snow", "中雪"),
    75: ("heavy snow", "大雪"),
    77: ("snow grains", "米雪"),
    80: ("light rain showers", "小阵雨"),
    81: ("rain showers", "阵雨"),
    82: ("heavy rain showers", "强阵雨"),
    85: ("light snow showers", "小阵雪"),
    86: ("heavy snow showers", "强阵雪"),
    95: ("thunderstorms", "雷暴"),
    96: ("thunderstorms with hail", "雷暴伴冰雹"),
    99: ("thunderstorms with heavy hail", "雷暴伴强冰雹"),
}


class StaleWeather(ValueError):
    def __init__(self, stamp):
        super().__init__("Outdated weather timestamp")
        self.stamp = stamp.isoformat()


def fresh_timestamp(value, now, max_age, zone=None):
    stamp = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        if zone is None:
            raise ValueError("Missing timezone")
        stamp = stamp.replace(tzinfo=zone)
    if not -300 <= (now - stamp).total_seconds() <= max_age:
        raise StaleWeather(stamp)
    return stamp


def number(value, minimum, maximum):
    if (
        type(value) not in (float, int)
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError("Weather value out of range")
    return value


def _condition(value, language):
    if type(value) is not int:
        return ""
    return WMO.get(value, ("", ""))[int(language == "zh")]


def _columns(data, group, expected):
    values, units = data[group], data[group + "_units"]
    times = values["time"]
    if units.get("time") != "unixtime" or not isinstance(times, list) or not times:
        raise ValueError("Missing weather dates")
    for field, unit in expected.items():
        if (
            units.get(field) != unit
            or not isinstance(values.get(field), list)
            or len(values[field]) != len(times)
        ):
            raise ValueError("Inconsistent forecast units or rows")
    return values


def _rain_windows(hourly, now, zone):
    """Hourly amounts/probabilities refer to the preceding hour, in local time."""
    windows = {}
    for i, stamp in enumerate(hourly["time"]):
        instant = datetime.fromtimestamp(stamp, UTC)
        end = instant.astimezone(zone)
        start = (instant - timedelta(hours=1)).astimezone(zone)
        amount, chance = hourly["precipitation"][i], hourly["precipitation_probability"][i]
        if instant <= now or amount is None or number(amount, 0, 2000) < 0.1:
            continue
        by_day = windows.setdefault(start.date().isoformat(), [])

        def hour_label(moment):
            label = moment.strftime("%H:%M")
            if moment.replace(fold=0).utcoffset() != moment.replace(fold=1).utcoffset():
                return f"{label} {moment.tzname()}"
            return label

        end_label = "24:00" if end.date() != start.date() else hour_label(end)
        start_label = hour_label(start)
        if by_day and by_day[-1]["until"] == start_label:
            by_day[-1]["until"] = end_label
        else:
            by_day.append({"from": start_label, "until": end_label})
        if chance is not None:
            chance = number(chance, 0, 100)
            by_day[-1]["peak_probability_pct"] = max(
                by_day[-1].get("peak_probability_pct", 0), chance
            )
    return windows


def world_forecast(read, place, language, now, horizon):
    params = {
        "latitude": place.latitude,
        "longitude": place.longitude,
        "timezone": place.timezone or "auto",
        "current": "temperature_2m,weather_code",
        "daily": ",".join(DAILY),
        "hourly": ",".join(HOURLY),
        "forecast_days": horizon,
        "timeformat": "unixtime",
    }
    data = read(OPEN_METEO_URL, params, ttl=600)
    zone = ZoneInfo(data["timezone"])
    today = now.astimezone(zone).date()
    current = data["current"]
    current_units = data["current_units"]
    if any(
        current_units.get(k) != v
        for k, v in {"temperature_2m": "°C", "weather_code": "wmo code", "time": "unixtime"}.items()
    ):
        raise ValueError("Invalid current units")
    result = {
        "timezone": zone.key,
        "source": "Open-Meteo",
        "source_url": "https://open-meteo.com/en/docs",
    }
    try:
        observed = fresh_timestamp(datetime.fromtimestamp(current["time"], zone), now, 7200)
        if current["temperature_2m"] is not None:
            result["current"] = {
                "time": observed.isoformat(),
                "temperature_c": number(current["temperature_2m"], -100, 70),
                "conditions": _condition(current["weather_code"], language),
                "basis": "model",
            }
    except StaleWeather as error:
        result["last_report_at"] = error.stamp
    daily = _columns(data, "daily", DAILY)
    dates = [datetime.fromtimestamp(d, zone).date() for d in daily["time"]]
    if any(b != a + timedelta(days=1) for a, b in zip(dates, dates[1:])):
        raise ValueError("Forecast dates are not consecutive")
    if dates[0] != today:
        raise StaleWeather(datetime.combine(dates[0], datetime.min.time(), tzinfo=zone))
    windows = _rain_windows(_columns(data, "hourly", HOURLY), now, zone)
    days = []
    for i, local_day in enumerate(dates):
        day = local_day.isoformat()
        row = {"date": day, "conditions": _condition(daily["weather_code"][i], language)}
        for name, field, low, high in (
            ("minimum_c", "temperature_2m_min", -100, 70),
            ("maximum_c", "temperature_2m_max", -100, 70),
            ("peak_precipitation_probability_pct", "precipitation_probability_max", 0, 100),
            ("precipitation_mm", "precipitation_sum", 0, 3000),
        ):
            if daily[field][i] is not None:
                row[name] = number(daily[field][i], low, high)
        if row.get("minimum_c", -100) > row.get("maximum_c", 70):
            raise ValueError("Inverted daily temperature range")
        if day in windows:
            row["precipitation_windows"] = windows[day][:3]
        if any(k not in {"date", "conditions"} for k in row) or row["conditions"]:
            days.append(row)
    return {**result, "days": days}
