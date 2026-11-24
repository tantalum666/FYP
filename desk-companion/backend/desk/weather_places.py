"""Resolve explicit public destinations without storing or requesting the owner's location."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
import math
import re
import unicodedata

import httpx
from opencc import OpenCC

PLACE_READS = ThreadPoolExecutor(max_workers=6, thread_name_prefix="weather-place")
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
HK_NAMES = {"hong kong", "hong_kong", "hongkong", "香港", "香港特别行政区", "香港特別行政區"}
COORDINATES = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)")
# GeoNames point features with a meaningful single forecast location. Regions,
# countries, ranges and other extended features need a more specific destination.
FIXED_SITE_CODES = {
    "AIRB",
    "AIRF",
    "AIRH",
    "AIRP",
    "AIRT",
    "RSTN",  # airfields, terminals and stations
    "LTHSE",
    "MUS",
    "OBS",
    "STDM",  # fixed landmarks
    "MT",
    "PK",
    "VLC",  # mountains, peaks and volcanoes
}
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


def _choices(rows, language):
    labels = [_label(row) for row in rows]
    repeated = {label for label in labels if labels.count(label) > 1}
    for i, row in enumerate(rows):
        if labels[i] in repeated:
            town = str(row.get("feature_code", "")).startswith("PPL")
            kind = (
                ("城镇" if town else "地点") if language == "zh" else ("town" if town else "site")
            )
            if isinstance(row.get("latitude"), (int, float)) and isinstance(
                row.get("longitude"), (int, float)
            ):
                labels[i] += f" ({kind}, {row['latitude']:.3f}, {row['longitude']:.3f})"
    return labels


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

    # The returned place name is localized. Use the input's script for an exact site
    # comparison, even when the requested weather reply is in the other language.
    place_language = "zh" if HAN.search(text) else "en" if text.isascii() else language

    def search(name):
        params = {"name": name, "count": 12, "language": place_language}
        if country_code:
            params["countryCode"] = country_code
        return read(GEOCODING_URL, params, ttl=86400).get("results", [])

    # Both scripts are needed for ambiguous names; overlap their independent public reads.
    futures = (
        {name: PLACE_READS.submit(search, name) for name in variants} if len(variants) > 1 else {}
    )
    found = {}
    failed_variant = None
    for name in variants:
        try:
            matches = futures[name].result() if futures else search(name)
        except (httpx.HTTPError, ValueError) as error:
            failed_variant = error
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
            raise failed_variant
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
    # The geocoder also returns fuzzy names. A similarly named airport is not
    # evidence for a mountain, and an airport and its nearby city have distinct coordinates.
    bare = simplified(text.partition(",")[0].strip().casefold())
    exact_cities = [r for r in cities if simplified(r["name"].casefold()) == bare]
    sites = [r for r in found.values() if r.get("feature_code") in FIXED_SITE_CODES]
    exact_sites = [r for r in sites if simplified(r["name"].casefold()) == bare]
    short_code = bool(re.fullmatch(r"[A-Za-z]{3,4}", text.partition(",")[0].strip()))
    if exact_sites:
        candidates = [*exact_sites, *exact_cities]
    elif not cities or (
        not exact_cities
        and (
            first in sites or (short_code and sites) or simplified(first["name"].casefold()) == bare
        )
    ):
        raise PlaceProblem("not_found")
    else:
        # Populated places retain their existing multilingual alias/population ranking.
        candidates = exact_cities or cities
    candidates.sort(key=_weight, reverse=True)
    top = candidates[0]
    if failed_variant and top.get("feature_code") != "PPLC" and _weight(top) < 100_000:
        raise failed_variant
    if len(candidates) > 1:
        second = candidates[1]
        dominant_city = (
            not exact_sites
            and _weight(top) >= 100_000
            and _weight(top) >= 8 * max(1, _weight(second))
        )
        if not dominant_city:
            raise PlaceProblem("ambiguous", _choices(candidates[:3], language))
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
