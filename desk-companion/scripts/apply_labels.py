"""Apply independently annotated time intervals to an extracted landmark replay."""

import argparse
import csv
import json
from pathlib import Path


def apply(rows, intervals):
    previous = -1.0
    for interval in sorted(intervals, key=lambda r: float(r["start_seconds"])):
        start, end = float(interval["start_seconds"]), float(interval["end_seconds"])
        if not 0 <= start < end or start < previous:
            raise ValueError("Label intervals overlap or have invalid times")
        previous = end
        if interval.get("calibration_pose") not in {"", "reference", "forward", "side"}:
            raise ValueError("Invalid setup phase")
        if not interval.get("calibration_pose") and interval.get("expected") not in {
            "within_reference",
            "forward",
            "side",
            "absent",
            "unknown",
        }:
            raise ValueError("Each scored interval needs a ground-truth label")
    result = []
    for row in rows:
        seconds = row["observation"]["captured_ms"] / 1000
        matches = [
            r for r in intervals if float(r["start_seconds"]) <= seconds < float(r["end_seconds"])
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Observation at {seconds:.3f}s does not have exactly one label interval"
            )
        label = matches[0]
        result.append(
            {
                **row,
                "expected": label.get("expected") or None,
                "calibration_pose": label.get("calibration_pose") or None,
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.observations.read_text().splitlines() if line.strip()]
    with args.labels.open(newline="") as file:
        intervals = list(csv.DictReader(file))
    labelled = apply(rows, intervals)
    with args.output.open("x") as file:
        for row in labelled:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        f"Applied supplied annotations to {len(labelled)} observations. Labels were not inferred by the model."
    )


if __name__ == "__main__":
    main()
