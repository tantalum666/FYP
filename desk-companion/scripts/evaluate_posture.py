"""Evaluate labelled landmark replays, keeping personal setup outside scoring.

Each JSONL row: participant, split (development/test), source (recorded/synthetic),
observation (Observation schema), expected (within_reference/forward/side/absent/
unknown), and optional calibration_pose (reference/forward/side).
No accuracy claim is generated when labels or completed calibrations are missing.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.posture import Observation, PostureEngine, PosturePreferences, features, classify  # noqa: E402

CLASSES = ["within_reference", "forward", "side", "absent", "unknown"]


def evaluate(rows, split="test"):
    participants = defaultdict(set)
    for row in rows:
        if row.get("split") not in {"development", "test"} or row.get("source") not in {
            "recorded",
            "synthetic",
        }:
            raise ValueError("Every row needs an explicit split and data source")
        participants[row["participant"]].add(row["split"])
    if any(len(splits) > 1 for splits in participants.values()):
        raise ValueError("A participant appears in both development and test data")
    rows = [row for row in rows if row["split"] == split]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["participant"], row.get("session", "default"))].append(row)
    matrix = {name: {other: 0 for other in CLASSES} for name in CLASSES}
    records = []
    scored = 0
    unknown = 0
    for (participant, session), clip in grouped.items():
        engine = PostureEngine()
        engine.configure(PosturePreferences(enabled=True))
        last_phase = None
        baseline_cooldown = 0
        baseline_prompts = []
        temporal_prompts = []
        observations = []
        clip.sort(key=lambda r: r["observation"]["captured_ms"])
        for row in clip:
            observation = Observation.model_validate(row["observation"])
            at = observation.captured_ms / 1000
            phase = row.get("calibration_pose")
            if phase and phase != last_phase:
                engine.begin_calibration(phase)
            last_phase = phase
            events = engine.ingest(
                observation,
                at,
                row["source"] == "recorded" and "live" or "replay",
                session + "-evaluation",
            )
            if phase:
                continue
            if len(engine.anchors) != 3:
                raise ValueError("Scored observations require three completed setup phases")
            expected = row.get("expected")
            if expected not in CLASSES:
                raise ValueError("Every scored observation needs a manual expected label")
            actual = engine.status if engine.status in CLASSES else "unknown"
            matrix[expected][actual] += 1
            scored += 1
            unknown += actual == "unknown"
            vector, _ = features(observation)
            instant = classify(vector, engine.anchors) if vector is not None else "unknown"
            if instant in {"forward", "side"} and at >= baseline_cooldown:
                baseline_prompts.append(at)
                baseline_cooldown = at + engine.preferences["cooldown_seconds"]
            temporal_prompts.extend(
                e["created_at"] for e in events if e["type"] == "posture_prompt"
            )
            observations.append((at, expected))
        episodes = []
        for at, label in observations:
            if episodes and episodes[-1]["label"] == label and at - episodes[-1]["end"] <= 2:
                episodes[-1]["end"] = at
            else:
                episodes.append({"start": at, "end": at, "label": label})

        def alert_metrics(prompts):
            valid = [
                e
                for e in episodes
                if e["label"] in {"forward", "side"}
                and e["end"] - e["start"] >= engine.preferences["persistence_seconds"]
            ]
            matched = set()
            false = 0
            latencies = []
            for at in prompts:
                index = next((i for i, e in enumerate(valid) if e["start"] <= at <= e["end"]), None)
                if index is None:
                    false += 1
                else:
                    matched.add(index)
                    latencies.append(
                        round(
                            at - valid[index]["start"] - engine.preferences["persistence_seconds"],
                            3,
                        )
                    )
            hours = (
                (observations[-1][0] - observations[0][0]) / 3600 if len(observations) > 1 else 0
            )
            return {
                "prompts": len(prompts),
                "brief_or_non_deviation_prompts": false,
                "false_prompts_per_hour": round(false / hours, 3) if hours else None,
                "eligible_episodes": len(valid),
                "episodes_with_prompt": len(matched),
                "delay_from_persistence_seconds": latencies,
                "negative_delay_means_premature": True,
            }

        records.append(
            {
                "participant": participant,
                "session": session,
                "split": clip[0]["split"],
                "source": clip[0]["source"],
                "single_frame_with_same_cooldown": alert_metrics(baseline_prompts),
                "sustained_with_reassessment": alert_metrics(temporal_prompts),
            }
        )
    if not scored:
        raise ValueError("No labelled observations to score")
    per_class = {}
    for label in CLASSES:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in CLASSES if other != label)
        fn = sum(matrix[label][other] for other in CLASSES if other != label)
        per_class[label] = {
            "support": sum(matrix[label].values()),
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        }
    supported = [v["f1"] for v in per_class.values() if v["support"] > 0]
    return {
        "evaluated_split": split,
        "data_sources": sorted({r["source"] for r in rows}),
        "recorded_input_only": all(r["source"] == "recorded" for r in rows),
        "validation_status": "requires independent review of collection and ground truth",
        "scored_frames": scored,
        "unknown_fraction": unknown / scored,
        "macro_f1_over_present_classes": sum(supported) / len(supported),
        "confusion_matrix": matrix,
        "per_class": per_class,
        "clips": records,
        "limitations": [
            "Personal calibration frames excluded from scoring.",
            "Temporal filtering changes prompt timing; frame classification is shared with the baseline.",
            "Synthetic inputs do not establish real camera accuracy, false alarms or health effects.",
            "Recorded labels and consent must be independently verified by the team.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "test"], default="test")
    args = parser.parse_args()
    if args.input.stat().st_size > 100_000_000:
        raise SystemExit("Split files larger than 100 MB")
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    report = evaluate(rows, args.split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("Report saved; inspect data_sources and limitations before citing results.")


if __name__ == "__main__":
    main()
