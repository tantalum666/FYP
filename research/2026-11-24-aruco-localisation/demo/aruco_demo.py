"""Five-marker planar localisation demo. Run with Python 3.11 or 3.12."""
import argparse
from collections import Counter, deque
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np


def read_layout(file):
    cfg = json.loads(Path(file).read_text(encoding="utf-8"))
    return validate_layout(cfg)


def validate_layout(cfg):
    references = cfg["reference_centres_mm"]
    if set(references) != {"0", "1", "2", "3"} or cfg["target_id"] != 4:
        raise ValueError("Use reference IDs 0,1,2,3 and target ID 4.")
    xy = np.array([references[str(i)] for i in range(4)], np.float32)
    width, depth = cfg["table_width_mm"], cfg["table_depth_mm"]
    if not (math.isfinite(width) and math.isfinite(depth) and width > 0 and depth > 0):
        raise ValueError("Table dimensions must be positive millimetres.")
    if xy.shape != (4, 2) or not np.isfinite(xy).all():
        raise ValueError("Supply four measured reference centres in millimetres.")
    if not cv2.isContourConvex(xy.reshape(-1, 1, 2)):
        raise ValueError("Reference centres must form a convex 0,1,2,3 outline.")
    if not ((xy >= 0).all() and (xy <= [width, depth]).all()):
        raise ValueError("Reference centres must lie on the configured table.")
    if not isinstance(cfg.get('allow_three_references', False), bool):
        raise ValueError('Three-reference mode must be true or false.')
    side = cfg.get('reference_marker_size_mm', 60)
    if not isinstance(side, (float, int)) or not math.isfinite(side) or side <= 0:
        raise ValueError('Reference black-square size must be positive millimetres.')
    if cfg.get('reference_layout_mode') == 'l_shape':
        expected = np.float32([[0,0],[width,0],[width,depth],[0,depth]])
        if not np.allclose(xy,expected,atol=.01) or not cfg.get('allow_three_references',False):
            raise ValueError('L 形记录需要正确的两段间距，请重新保存记录。')
    return cfg


def diagonal_centre(corners):
    """A square's physical centre projects to its diagonal intersection."""
    homogeneous = np.column_stack([corners, np.ones(4)])
    point = np.cross(np.cross(homogeneous[0], homogeneous[2]),
                     np.cross(homogeneous[1], homogeneous[3]))
    if abs(point[2]) < 1e-9:
        raise ValueError("Degenerate marker quadrilateral.")
    return point[:2] / point[2]


def locate(markers, cfg):
    """Recompute the mapping from visible references on each frame."""
    counts = Counter(marker_id for marker_id, _ in markers)
    ids = sorted(counts)
    result = {"ids": ids, "status": "WAITING_REFERENCES", "pose": None}
    l_shape = cfg.get('reference_layout_mode') == 'l_shape'
    required_ids = (0,1,2,4) if l_shape else range(5)
    if any(counts[i] > 1 for i in required_ids):
        result["status"] = "DUPLICATE_ID"
        return result
    by_id = dict(markers)
    visible_references = [i for i in (range(3) if l_shape else range(4)) if i in by_id]
    use_three = len(visible_references) == 3 and cfg.get('allow_three_references', False)
    if len(visible_references) < 4 and not use_three:
        return result
    try:
        pixels = np.array([diagonal_centre(by_id[i]) for i in visible_references], np.float32)
        if not np.isfinite(pixels).all() or not cv2.isContourConvex(pixels.reshape(-1, 1, 2)):
            raise ValueError("Invalid reference layout in the image.")
        if abs(cv2.contourArea(pixels)) < 100:
            raise ValueError("Reference polygon is too small.")
        if use_three:
            # Three centres cannot determine a homography. Use all 12 corners,
            # with explicitly measured square sizes and fixed marker orientation.
            half = cfg.get('reference_marker_size_mm', 60)/2
            offsets = np.float32([[-half,half],[half,half],[half,-half],[-half,-half]])
            source = np.concatenate([by_id[i] for i in visible_references]).astype(np.float32)
            world = np.concatenate([offsets+cfg['reference_centres_mm'][str(i)] for i in visible_references]).astype(np.float32)
            mapping, _ = cv2.findHomography(source, world, method=0)
            if mapping is None:
                raise ValueError('Cannot fit the three reference markers.')
            fitted = cv2.perspectiveTransform(source.reshape(1,-1,2), mapping)[0]
            residual = float(np.linalg.norm(fitted-world, axis=1).max())
            limit = max(3., half*.16)
            if math.isfinite(residual):
                result['mapping_error_mm'] = residual
            result['mapping_error_limit_mm'] = limit
            if not math.isfinite(residual) or residual > limit:
                result['geometry_hint'] = ('三牌角点与当前标定不一致。请按纸牌现在的位置填写码中心实测 X/Y，'
                    '不要临时摆牌却沿用默认桌角坐标；同时确认黑框边长、统一朝向及码面同高。')
                if l_shape:
                    result['geometry_hint'] = '三张牌还没有对上。请按图摆成直角 L：0 和 1 左右对齐，1 和 2 前后对齐；量黑框中心间距，三张牌平放且上边朝远侧。'
                result['geometry_error_code'] = 'REFERENCE_CALIBRATION_MISMATCH'
                raise ValueError('Three-reference corner fit disagrees with the configured sizes or orientation.')
        else:
            world = np.array([cfg['reference_centres_mm'][str(i)] for i in range(4)], np.float32)
            mapping = cv2.getPerspectiveTransform(pixels, world)
        if not np.isfinite(mapping).all() or np.linalg.matrix_rank(mapping) < 3:
            raise ValueError("Invalid homography.")
    except (ValueError, np.linalg.LinAlgError) as error:
        result["status"] = "INVALID_GEOMETRY"
        result['geometry_error'] = str(error)
        result.setdefault('geometry_hint', '参照牌几何无法建立坐标。请检查码中心实测坐标、摆放顺序，并把码平放在同一桌面。')
        return result
    result["homography"] = mapping.tolist()
    result['reference_ids_used'] = visible_references
    result['mapping_mode'] = 'three_marker_corners' if use_three else 'four_centres'
    if 4 not in by_id:
        result["status"] = "TARGET_LOST"
        return result
    projected = cv2.perspectiveTransform(by_id[4].reshape(1, 4, 2).astype(np.float32), mapping)[0]
    x, y = projected.mean(axis=0)
    forward = (projected[0] + projected[1]) / 2 - [x, y]
    if not np.isfinite(projected).all() or np.linalg.norm(forward) < 1e-6:
        result["status"] = "INVALID_GEOMETRY"
        return result
    heading = math.degrees(math.atan2(float(forward[0]), float(forward[1]))) % 360
    result["pose"] = [float(x), float(y), heading]
    result["status"] = "TRACKING" if 0 <= x <= cfg["table_width_mm"] and 0 <= y <= cfg["table_depth_mm"] else "OUTSIDE_TABLE"
    return result


def locate_image(markers):
    """Track ID 4 in image pixels without assuming any physical calibration."""
    counts = Counter(i for i, _ in markers)
    result = {'ids':sorted(counts), 'status':'TARGET_LOST', 'pose':None,
              'coordinate_mode':'image', 'coordinate_units':'px', 'mapping_mode':'image_pixels'}
    if counts[4] > 1:
        result['status'] = 'DUPLICATE_ID'
        return result
    if counts[4] != 1:
        return result
    corners = dict(markers)[4]
    try:
        centre = diagonal_centre(corners)
        forward = (corners[0]+corners[1])/2-centre
        if not np.isfinite(centre).all() or np.linalg.norm(forward) < 1e-6:
            raise ValueError('Invalid image marker geometry.')
    except ValueError:
        result['status'] = 'INVALID_GEOMETRY'
        return result
    heading = math.degrees(math.atan2(float(forward[0]), -float(forward[1]))) % 360
    result['pose'] = [float(centre[0]), float(centre[1]), heading]
    result['status'] = 'TRACKING'
    return result


def marker_positions(markers, result, cfg):
    """Report image coordinates separately from calibrated reference positions."""
    counts = Counter(i for i, _ in markers)
    by_id = dict(markers)
    positions = []
    for marker_id in range(5):
        item = {'id':marker_id, 'visible':counts[marker_id] > 0,
                'duplicate':counts[marker_id] > 1, 'image_px':None, 'table_mm':None,
                'coordinate_source':('image_pixels' if result.get('coordinate_mode') == 'image' else
                                     'calibration' if marker_id < 4 else 'vision')}
        unused = cfg.get('reference_layout_mode') == 'l_shape' and marker_id == 3
        if unused:
            item['coordinate_source'] = 'not_used'
        if counts[marker_id] == 1:
            try:
                item['image_px'] = np.round(diagonal_centre(by_id[marker_id]),1).tolist()
            except ValueError:
                pass
            if result.get('homography') is not None:
                if marker_id < 4 and not unused:
                    item['table_mm'] = list(cfg['reference_centres_mm'][str(marker_id)])
                elif marker_id == 4 and result.get('pose') is not None:
                    item['table_mm'] = result['pose'][:2]
        positions.append(item)
    return positions


def detect(frame, detector):
    corners, ids, _ = detector.detectMarkers(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    if ids is None:
        return []
    return [(int(marker_id), c.reshape(4, 2)) for marker_id, c in zip(ids.flatten(), corners)]


def label(frame, text, y, color=(30, 55, 30)):
    cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 4, cv2.LINE_AA)
    cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 1, cv2.LINE_AA)


def camera_view(frame, markers, result):
    display = frame.copy()
    if markers:
        cv2.aruco.drawDetectedMarkers(display, [c.reshape(1, 4, 2) for _, c in markers],
                                     np.array([[i] for i, _ in markers], np.int32))
    label(display, f"IDs {result['ids']}   {result['status']}", 27)
    if result["pose"] is not None:
        x, y, angle = result["pose"]
        label(display, f"ID4   X {x:.1f} mm   Y {y:.1f} mm   heading {angle:.1f} deg", 54)
    else:
        label(display, "Position unavailable in this frame", 54, (20, 20, 185))
    return display


def table_view(cfg, result, trail):
    width, depth = cfg["table_width_mm"], cfg["table_depth_mm"]
    scale = min(840 / width, 430 / depth)
    image = np.full((540, 960, 3), 246, np.uint8)
    def point(x, y):
        return (int(55 + x * scale), int(470 - y * scale))
    cv2.rectangle(image, point(0, 0), point(width, depth), (90, 120, 100), 2)
    for key, (x, y) in cfg["reference_centres_mm"].items():
        cv2.circle(image, point(x, y), 6, (150, 70, 30), -1)
        cv2.putText(image, key, point(x+12, y-25), cv2.FONT_HERSHEY_SIMPLEX, .55, (90, 60, 30), 1)
    for first, second in zip(trail, list(trail)[1:]):
        if first is not None and second is not None:
            cv2.line(image, point(*first), point(*second), (165, 170, 165), 2)
    if result["pose"] is not None:
        x, y, angle = result["pose"]
        theta = math.radians(angle)
        cv2.circle(image, point(x, y), 8, (40, 140, 30), -1)
        cv2.arrowedLine(image, point(x, y), point(x+60*math.sin(theta), y+60*math.cos(theta)), (30, 80, 210), 3)
    label(image, f"TABLE MAP   {width:g} x {depth:g} mm   {result['status']}", 28)
    label(image, "Origin: near-left. X right, Y away. Heading: 0 away, 90 right.", 502)
    label(image, "Grey line: observed movement history. Q quit; S save evidence.", 527)
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="0", help="Camera index (0/1) or a saved video file")
    parser.add_argument("--layout", type=Path, default=Path(__file__).with_name("layout.json"))
    parser.add_argument("--output", type=Path, default=Path("runs"))
    parser.add_argument("--headless", action="store_true", help="Process a recording without display windows")
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args()
    cfg = read_layout(args.layout)
    source = int(args.source) if args.source.isdecimal() else args.source
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise SystemExit("Cannot open source. Check camera permission/index or the video path.")
    if isinstance(source, int):
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    output = args.output / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output.mkdir(parents=True)
    (output / "layout_used.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
    trail, counts, frames, full_ids = deque(maxlen=4000), Counter(), 0, 0
    input_fps = capture.get(cv2.CAP_PROP_FPS)
    started = time.monotonic()
    actual_size = None
    preview = overview = None
    try:
        with (output / "positions.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["frame", "source_time_s", "ids", "status", "x_mm", "y_mm", "heading_deg"])
            while not args.max_frames or frames < args.max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                frames += 1
                actual_size = [frame.shape[1], frame.shape[0]]
                markers = detect(frame, detector)
                result = locate(markers, cfg)
                counts[result["status"]] += 1
                full_ids += all(i in result["ids"] for i in range(5))
                source_time = ""
                if isinstance(source, int):
                    source_time = time.monotonic()-started
                elif input_fps > 0:
                    source_time = (frames-1)/input_fps
                pose = result["pose"]
                writer.writerow([frames, source_time, " ".join(map(str, result["ids"])), result["status"], *(pose or ["", "", ""])])
                trail.append(pose[:2] if pose else None)
                preview, overview = camera_view(frame, markers, result), table_view(cfg, result, trail)
                if args.headless:
                    continue
                cv2.imshow("Camera: marker detection", preview)
                cv2.imshow("Table: measured position", overview)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break
                if key == ord("s"):
                    cv2.imwrite(str(output/f"camera_{frames:05d}.png"), preview)
                    cv2.imwrite(str(output/f"table_{frames:05d}.png"), overview)
    except KeyboardInterrupt:
        pass
    finally:
        capture.release()
        if not args.headless:
            cv2.destroyAllWindows()
    elapsed = time.monotonic()-started
    summary = {"frames": frames, "all_five_visible_frames": full_ids,
               "all_five_visible_fraction": full_ids/frames if frames else None,
               "status_frames": dict(counts), "processing_fps": frames/elapsed,
               "actual_frame_size": actual_size, "opencv_version": cv2.__version__,
               "plane_assumption": "All five marker faces at the same height; uncorrected lens distortion.",
               "source": args.source}
    (output/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if preview is not None:
        cv2.imwrite(str(output/"last_camera.png"), preview)
        cv2.imwrite(str(output/"last_table.png"), overview)
    print(f"Saved {frames} frames of results to {output.resolve()}")
    if frames == 0:
        raise SystemExit("No frames were read. Check your source and repeat the test.")


if __name__ == "__main__":
    main()
