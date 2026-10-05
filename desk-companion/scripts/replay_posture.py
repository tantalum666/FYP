"""Explicit, visibly labelled synthetic sensor input for an isolated demo runtime."""

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx


def observation(pose, sequence):
    coordinates = {
        "reference": [(0.5, 0.30), (0.4, 0.60), (0.6, 0.60), (0.45, 0.32), (0.55, 0.32)],
        "forward": [(0.5, 0.39), (0.37, 0.60), (0.63, 0.60), (0.43, 0.40), (0.57, 0.40)],
        "side": [(0.58, 0.30), (0.4, 0.60), (0.6, 0.60), (0.53, 0.32), (0.63, 0.32)],
    }
    names = ["nose", "left_shoulder", "right_shoulder", "left_ear", "right_ear"]
    return {
        "sequence": sequence,
        "captured_ms": round(time.time() * 1000),
        "camera_id": "synthetic-demo-camera",
        "frame_width": 640,
        "frame_height": 480,
        "person_count": 0 if pose == "away" else 1,
        "brightness": 5 if pose == "dark" else 110,
        "landmarks": {
            name: {"x": x, "y": y, "visibility": 0.98, "presence": 0.98}
            for name, (x, y) in zip(names, coordinates.get(pose, coordinates["reference"]))
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8832")
    parser.add_argument("--runtime", type=Path, default=Path(".runtime/completion-qa"))
    parser.add_argument(
        "--pose", choices=["reference", "forward", "side", "away", "dark"], default="reference"
    )
    parser.add_argument(
        "--control", type=Path, help="Optional local fixture file containing the current pose"
    )
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument(
        "--recover-after-prompt",
        action="store_true",
        help="Synthetic participant returns to reference after the next new prompt",
    )
    args = parser.parse_args()
    boot = uuid4().hex
    started = time.time()
    recovered = False
    token = json.loads((args.runtime / "agent.json").read_text())["token"]
    with httpx.Client(
        trust_env=False,
        base_url=args.api,
        timeout=3,
        headers={"Authorization": "Bearer " + token, "X-Desk-Request": "1"},
    ) as client:
        config = client.get("/api/agent/config")
        config.raise_for_status()
        if not config.json()["replay_allowed"]:
            raise SystemExit("This runtime does not permit replay.")
        finish = time.monotonic() + min(3600, max(1, args.seconds))
        sequence = 0
        while time.monotonic() < finish:
            config = client.get("/api/agent/config")
            config.raise_for_status()
            config = config.json()
            if config["camera_enabled"]:
                pose = config["calibration_phase"] or (
                    args.control.read_text().strip()
                    if args.control and args.control.exists()
                    else args.pose
                )
                if recovered and not config["calibration_phase"]:
                    pose = "reference"
                response = client.post(
                    "/api/agent/observations",
                    json={
                        "boot_id": boot,
                        "source": "replay",
                        "observations": [observation(pose, sequence)],
                    },
                )
                response.raise_for_status()
                feedback = response.json()["posture"].get("feedback")
                if (
                    args.recover_after_prompt
                    and feedback
                    and feedback["created_at"] >= started
                    and feedback["outcome"] == "waiting"
                ):
                    recovered = True
                sequence += 1
            time.sleep(0.25)
    print("Synthetic replay finished; no camera was opened.")


if __name__ == "__main__":
    main()
