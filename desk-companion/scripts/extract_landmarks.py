"""Convert an explicitly supplied video into local, unlabelled landmark JSONL.

This never opens a camera, uploads frames, or guesses ground-truth labels. Obtain
consent before collecting the source video. Add labels and setup phases separately.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from desk.agents.camera import observation  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--split", choices=["development", "test"], required=True)
    parser.add_argument("--source", choices=["recorded", "synthetic"], required=True)
    args = parser.parse_args()
    import cv2
    import mediapipe as mp

    root = Path(__file__).resolve().parents[1]
    model = root / ".runtime/models/pose_landmarker_lite.task"
    # Same pinned model as the live camera worker.
    if (
        hashlib.sha256(model.read_bytes()).hexdigest()
        != "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
    ):
        raise ValueError("Model checksum mismatch")
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(model), delegate=mp.tasks.BaseOptions.Delegate.CPU
        ),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=2,
    )
    capture = cv2.VideoCapture(str(args.video))
    if not capture.isOpened():
        raise SystemExit("Unable to open the supplied video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not 1 <= fps <= 240:
        raise SystemExit("Video frame rate is unavailable")
    step = max(1, round(fps / 5))
    index = 0
    sequence = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector,
            args.output.open("x") as file,
        ):
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                current = index
                index += 1
                if current % step:
                    continue
                milliseconds = round(current / fps * 1000)
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                )
                result = detector.detect_for_video(image, milliseconds)
                sample = observation(
                    result, frame, milliseconds / 1000, sequence, "offline-labelled-video"
                )
                file.write(
                    json.dumps(
                        {
                            "participant": args.participant,
                            "session": args.session,
                            "split": args.split,
                            "source": args.source,
                            "expected": None,
                            "calibration_pose": None,
                            "observation": sample,
                        }
                    )
                    + "\n"
                )
                sequence += 1
    finally:
        capture.release()
    print(f"Wrote {sequence} unlabelled observations. No source video was copied or uploaded.")


if __name__ == "__main__":
    main()
