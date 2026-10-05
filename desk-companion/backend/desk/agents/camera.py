"""Run explicitly with --camera INDEX or --video FILE. No images are uploaded or saved."""

import argparse
import hashlib
import json
import math
import threading
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

import httpx


class LatestFrame:
    def __init__(self, capture):
        self.capture = capture
        self.lock = threading.Lock()
        self.latest = None
        self.last_success = time.monotonic()
        self.alive = True
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        while self.alive:
            ok, frame = self.capture.read()
            with self.lock:
                self.latest = (frame, time.time()) if ok else None
                if ok:
                    self.last_success = time.monotonic()
            if not ok:
                time.sleep(0.1)

    def take(self):
        with self.lock:
            item, self.latest = self.latest, None
            return item

    def close(self):
        self.alive = False
        self.capture.release()
        self.thread.join(timeout=2)


def observation(result, frame, captured, sequence, camera_id):
    import cv2

    points = {}
    if len(result.pose_landmarks) == 1:
        names = {
            0: "nose",
            7: "left_ear",
            8: "right_ear",
            11: "left_shoulder",
            12: "right_shoulder",
        }
        for index, name in names.items():
            if index >= len(result.pose_landmarks[0]):
                continue
            p = result.pose_landmarks[0][index]
            if (
                all(
                    isinstance(v, (int, float)) and math.isfinite(v)
                    for v in (p.x, p.y, p.visibility, p.presence)
                )
                and -0.2 <= p.x <= 1.2
                and -0.2 <= p.y <= 1.2
            ):
                points[name] = {
                    "x": p.x,
                    "y": p.y,
                    "visibility": p.visibility,
                    "presence": p.presence,
                }
    return {
        "sequence": sequence,
        "captured_ms": int(captured * 1000),
        "camera_id": camera_id,
        "frame_width": frame.shape[1],
        "frame_height": frame.shape[0],
        "person_count": len(result.pose_landmarks),
        "brightness": float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()),
        "landmarks": points,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--camera", type=int)
    source.add_argument("--video", type=Path)
    parser.add_argument("--api", default="http://127.0.0.1:8831")
    parser.add_argument(
        "--runtime", type=Path, default=Path(__file__).resolve().parents[3] / ".runtime"
    )
    parser.add_argument("--model", type=Path)
    parser.add_argument("--fps", type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.fps <= 15:
        parser.error("fps must be between 1 and 15")
    api_url = urlsplit(args.api)
    if (
        api_url.username
        or api_url.password
        or api_url.query
        or api_url.fragment
        or api_url.path
        or not (
            api_url.scheme == "https"
            or api_url.scheme == "http"
            and api_url.hostname in {"127.0.0.1", "localhost"}
        )
    ):
        parser.error("Use TLS for a non-loopback API")
    import cv2
    import mediapipe as mp

    model = args.model or args.runtime / "models/pose_landmarker_lite.task"
    if not model.exists():
        parser.error("Run scripts/fetch_models.py first, or supply --model")
    if (
        not args.model
        and hashlib.sha256(model.read_bytes()).hexdigest()
        != "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
    ):
        parser.error("Model checksum mismatch; run scripts/fetch_models.py")
    token = json.loads((args.runtime / "agent.json").read_text())["token"]
    camera_id = (
        f"uvc:{args.camera}:640x480" if args.camera is not None else f"video:{args.video.name}"
    )
    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(model), delegate=mp.tasks.BaseOptions.Delegate.CPU
        ),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )
    capture, latest = None, None
    boot, sequence, last_ms = uuid4().hex, 0, -1
    try:
        with (
            mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector,
            httpx.Client(
                trust_env=False,
                timeout=2,
                headers={"Authorization": "Bearer " + token, "X-Desk-Request": "1"},
            ) as api,
        ):
            while True:
                started = time.monotonic()
                try:
                    control = api.get(args.api + "/api/agent/config")
                    control.raise_for_status()
                    if not control.json()["camera_enabled"]:
                        if latest:
                            latest.close()
                        elif capture:
                            capture.release()
                        capture, latest = None, None
                        time.sleep(0.5)
                        continue
                    if capture is None:
                        capture = cv2.VideoCapture(
                            args.camera if args.camera is not None else str(args.video)
                        )
                        if not capture.isOpened():
                            capture.release()
                            capture = None
                            time.sleep(1)
                            continue
                        if args.camera is not None:
                            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            latest = LatestFrame(capture)
                    if latest:
                        item = latest.take()
                        if item is None:
                            if time.monotonic() - latest.last_success > 3:
                                latest.close()
                                capture, latest = None, None
                            time.sleep(0.05)
                            continue
                        frame, captured = item
                        if time.time() - captured > 1:
                            continue
                    else:
                        ok, frame = capture.read()
                        if not ok:
                            break
                        captured = time.time()
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    timestamp_ms = max(last_ms + 1, int(time.monotonic() * 1000))
                    result = detector.detect_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms
                    )
                    last_ms = timestamp_ms
                    data = observation(result, frame, captured, sequence, camera_id)
                    response = api.post(
                        args.api + "/api/agent/observations",
                        json={
                            "source": "live" if latest else "replay",
                            "boot_id": boot,
                            "observations": [data],
                        },
                    )
                    response.raise_for_status()
                    sequence += 1
                except httpx.HTTPError:
                    # Loss of control closes capture instead of recording an unseen backlog.
                    if latest:
                        latest.close()
                    elif capture:
                        capture.release()
                    capture, latest = None, None
                    time.sleep(0.5)
                time.sleep(max(0, 1 / args.fps - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        if latest:
            latest.close()
        elif capture:
            capture.release()


if __name__ == "__main__":
    main()
