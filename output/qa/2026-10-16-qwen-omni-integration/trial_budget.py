"""Conservative reservations for this explicitly authorized CNY5 synthetic trial."""

import fcntl
import json
from pathlib import Path

PATH = Path(__file__).with_name("trial-budget.json")


def reserve(kind, amount=1):
    with PATH.open("r+") as file:
        fcntl.flock(file.fileno(), fcntl.LOCK_EX)
        data = json.load(file)
        used = sum(row["reserve_cny"] for row in data["requests"])
        if used + amount > data["authorized_cny"]:
            raise RuntimeError("TRIAL_BUDGET_EXHAUSTED")
        number = len(data["requests"]) + 1
        data["requests"].append({"number": number, "kind": kind, "reserve_cny": amount})
        file.seek(0)
        json.dump(data, file, indent=2)
        file.write("\n")
        file.truncate()
        return number
