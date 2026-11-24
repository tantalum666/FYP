"""Rebuild the offline airport/timezone index from a verified airportsdata wheel."""

import argparse
import csv
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

VERSION = "20261103"
DIGEST = "a55a2a33785d722d57c67010e055f3c229e1281a5326b9d4810863f4ee2367d2"
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    payload = args.wheel.read_bytes()
    if hashlib.sha256(payload).hexdigest() != DIGEST:
        parser.error(f"Expected the official airportsdata {VERSION} wheel")
    by_code = defaultdict(set)
    with ZipFile(io.BytesIO(payload)) as wheel:
        with wheel.open("airportsdata/airports.csv") as table:
            for row in csv.DictReader(io.TextIOWrapper(table, encoding="utf-8")):
                code, zone = row["iata"], row["tz"]
                if len(code) == 3 and code.isascii() and code.isalpha() and code.isupper() and zone:
                    ZoneInfo(zone)
                    by_code[code].add(zone)
        license_text = wheel.read(f"airportsdata-{VERSION}.dist-info/licenses/LICENSE")
    groups = defaultdict(list)
    for code, zones in sorted(by_code.items()):
        if len(zones) == 1:
            groups[next(iter(zones))].append(code)
    data = {zone: " ".join(codes) for zone, codes in sorted(groups.items())}
    (ROOT / "backend/desk/data/airport-timezones.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "licenses/airportsdata-LICENSE.txt").write_bytes(license_text)


if __name__ == "__main__":
    main()
