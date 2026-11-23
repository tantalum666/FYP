"""Resolve explicit public destinations without storing or requesting the owner's location."""

from dataclasses import dataclass
from functools import lru_cache
import math
import re
import unicodedata

import httpx
from opencc import OpenCC

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
HK_NAMES = {"hong kong", "hong_kong", "hongkong", "香港", "香港特别行政区", "香港特別行政區"}
COORDINATES = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)")
HAN = re.compile(r"[\u3400-\u9fff]")


@lru_cache(maxsize=2)
def _converter(direction):
    return OpenCC(direction)


def simplified(text):
    return _converter("t2s").convert(text) if HAN.search(text) else text


@dataclass(frozen=True)
class Place:
    name: str
    latitude: float
    longitude: float
    country: str = ""
    region: str = ""
    code: str = ""
    timezone: str = ""


HONG_KONG = Place("Hong Kong", 22.30, 114.17, code="HK", timezone="Asia/Hong_Kong")


class PlaceProblem(ValueError):
    def __init__(self, reason, choices=()):
        super().__init__(reason)
        self.reason = reason
        self.choices = list(choices)


def _label(row):
    return ", ".join(
        dict.fromkeys(str(row[k])[:90] for k in ("name", "admin1", "country") if row.get(k))
    )


def _weight(row):
    value = row.get("population")
    return value if type(value) is int and value > 0 else 0


def resolve_place(read, location, country_code, language):
    text = unicodedata.normalize("NFKC", location).strip()
    if text.casefold() in {
        "here",
        "near me",
        "my location",
        "当地",
        "本地",
        "这里",
        "這裡",
        "附近",
        "我这边",
    }:
        raise PlaceProblem("missing_city")
    if text.casefold() in HK_NAMES and country_code in (None, "HK", "CN"):
        return HONG_KONG
    if match := COORDINATES.fullmatch(text):
        lat, lon = (float(x) for x in match.groups())
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise PlaceProblem("invalid_coordinates")
        lat, lon = round(lat, 1), round(lon, 1)
        return Place(f"{lat:.1f}, {lon:.1f}", lat, lon)

    # GeoNames has distinct alternate-name entries for the two Chinese scripts.
    # Some simplified forms also name unrelated villages. Rank across both scripts.
    variants = [text]
    if HAN.search(text):
        variants = list(dict.fromkeys([_converter("s2t").convert(text), simplified(text)]))
    found = {}
    failed_variant = False
    for name in variants:
        params = {"name": name, "count": 12, "language": language}
        if country_code:
            params["countryCode"] = country_code
        try:
            matches = read(GEOCODING_URL, params, ttl=86400).get("results", [])
        except (httpx.HTTPError, ValueError):
            failed_variant = True
            continue
        for row in matches:
            if isinstance(row, dict) and row.get("id") and row.get("name"):
                if not country_code or row.get("country_code") == country_code:
                    found.setdefault(row["id"], row)
    qualifiers = [q.strip() for q in text.split(",")[2:]]
    if qualifiers:
        # GeoNames applies only the first comma qualifier. Verify any trailing country.
        found = {
            k: r
            for k, r in found.items()
            if all(
                simplified(q.casefold())
                in {
                    simplified(str(r.get(f, "")).casefold())
                    for f in ("country", "country_code", "admin1")
                }
                for q in qualifiers
            )
        }
    if not found:
        if failed_variant:
            raise ValueError("Place service unavailable")
        raise PlaceProblem("not_found")
    first = next(iter(found.values()))
    cities = [r for r in found.values() if str(r.get("feature_code", "")).startswith("PPL")]
    # A country's centre is not representative weather for its population.
    # Keep city-states when the same name genuinely identifies a populated place.
    broad = str(first.get("feature_code", "")).startswith(("PCL", "ADM"))
    if broad and not any(
        r["name"] == first["name"] and r.get("country_code") == first.get("country_code")
        for r in cities
    ):
        raise PlaceProblem("specify_city")
    if not cities:
        raise PlaceProblem("specify_city" if broad else "not_found")

    # Exact display names precede fuzzy matches. The service also matches aliases in
    # other languages, so retain its ranking when the returned language differs.
    bare = simplified(text.partition(",")[0].strip().casefold())
    exact = [r for r in cities if simplified(r["name"].casefold()) == bare]
    candidates = exact or cities
    candidates.sort(key=_weight, reverse=True)
    top = candidates[0]
    if failed_variant and top.get("feature_code") != "PPLC" and _weight(top) < 100_000:
        # A village in one script is insufficient when we could not resolve the other.
        raise ValueError("Incomplete place search")
    if len(candidates) > 1:
        second = candidates[1]
        dominant = _weight(top) >= 100_000 and _weight(top) >= 8 * max(1, _weight(second))
        if not dominant:
            raise PlaceProblem("ambiguous", [_label(r) for r in candidates[:3]])
    lat, lon = float(top["latitude"]), float(top["longitude"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid public coordinates")
    if top.get("country_code") == "HK" and top.get("feature_code") == "PPLC":
        return HONG_KONG
    return Place(
        top["name"],
        round(lat, 2),
        round(lon, 2),
        top.get("country", ""),
        top.get("admin1", ""),
        top.get("country_code", ""),
        top.get("timezone", ""),
    )
