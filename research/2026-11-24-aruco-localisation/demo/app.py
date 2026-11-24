"""Local camera/video interface for the existing ArUco localisation engine."""
import argparse
import base64
import errno
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import time
from urllib.request import urlopen
import webbrowser

import cv2
import numpy as np

from aruco_demo import detect, locate, locate_image, marker_positions, read_layout, validate_layout
from obstacles import ObstacleDetector, project_obstacles
from monitoring import desk_region, edge_monitor, intersects_region, change_candidates, proximity_monitor


ROOT = Path(__file__).resolve().parent
OBSTACLE_DETECTOR = None
OBSTACLE_ERROR = None
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/sample.mp4": ("sample.mp4", "video/mp4"),
    "/l_shape_guide.svg": ("l_shape_guide.svg", "image/svg+xml"),
}


def decode_frame(value, error_message):
    if not isinstance(value, str) or not value:
        raise ValueError(error_message)
    encoded = value.split(",", 1)[-1]
    try:
        raw = base64.b64decode(encoded, validate=True)
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    except (ValueError, cv2.error) as exc:
        raise ValueError(error_message) from exc
    if image is None or max(image.shape[:2]) > 4096:
        raise ValueError(error_message)
    return image


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if not self.path.startswith("/api/frame"):
            super().log_message(format, *args)

    def json_response(self, status, data):
        payload = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-ArUco-Engine", "local-v1")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route == "/api/layout":
            self.json_response(200, read_layout(ROOT/"layout.json"))
            return
        asset = ASSETS.get(route)
        if asset is None:
            self.send_error(404)
            return
        file, content_type = asset
        data = (ROOT/file).read_bytes()
        first, last, status = 0, len(data)-1, 200
        requested = self.headers.get("Range")
        if requested:
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", requested)
            if not match or int(match[1]) >= len(data):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(data)}")
                self.end_headers()
                return
            first = int(match[1])
            last = min(int(match[2] or last), last)
            if last < first:
                self.send_error(416)
                return
            status = 206
        payload = data[first:last+1]
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {first}-{last}/{len(data)}")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/api/frame":
            self.send_error(404)
            return
        expected_origin = f"http://{self.headers.get('Host')}"
        if self.headers.get("Origin") not in (None, expected_origin):
            self.json_response(403, {"error": "请从本机定位台页面操作。"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4_000_000:
                raise ValueError("图像过大或请求为空。")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('请求必须是 JSON 对象。')
            mode = payload.get('coordinate_mode', 'table')
            if mode not in ('image', 'table'):
                raise ValueError('请选择像素演示或桌面定位模式。')
            layout = validate_layout(payload['layout']) if mode == 'table' else {}
            image = decode_frame(payload.get("image"), "无法读取图像，或分辨率超过 4096。")
            started = time.perf_counter()
            detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
            markers = detect(image, detector)
            result = locate_image(markers) if mode == 'image' else locate(markers, layout)
            result['coordinate_mode'] = mode
            result['coordinate_units'] = 'px' if mode == 'image' else 'mm'
            result['image_size_px'] = [image.shape[1], image.shape[0]]
            result['marker_positions'] = marker_positions(markers, result, layout)
            result["corners"] = [{"id": i, "points": c.tolist()} for i, c in markers]
            region, region_source = desk_region(payload.get('desk_polygon_normalized'),result,layout,image.shape[1],image.shape[0])
            result['desk_polygon_px'] = region.tolist() if region is not None else None
            result['desk_region_source'] = region_source
            result.update(edge_monitor(markers,result,region,image.shape[1],image.shape[0]))
            if region_source == 'calibrated_test_area_projection':
                result['edge_message'] = result['edge_message'].replace('桌面范围','L 形测试区域').replace('桌面边界','测试区域边界').replace('桌边','测试区域边界')
            result['obstacles'] = []
            result['obstacle_status'] = 'disabled'
            if payload.get('detect_objects', True):
                result['obstacle_status'] = 'unavailable'
                if OBSTACLE_DETECTOR is not None:
                    try:
                        confidence = float(payload.get('object_confidence', .4))
                        if not .2 <= confidence <= .9:
                            raise ValueError('物品识别置信度应在 0.2 到 0.9 之间。')
                        objects = [obj for obj in OBSTACLE_DETECTOR.detect(image, confidence) if intersects_region(obj['box_px'],region)]
                        result['obstacles'] = project_obstacles(objects, result.get('homography'), layout)
                        result['obstacle_status'] = 'ready'
                    except (cv2.error, ValueError) as error:
                        result['obstacle_error'] = str(error)
                else:
                    result['obstacle_error'] = OBSTACLE_ERROR
            result['semantic_status'] = result['obstacle_status']
            result['generic_status'] = 'disabled'
            result['generic_message'] = '未知物品检测已关闭。'
            if payload.get('detect_unknown',False):
                reference = None
                background = payload.get('background_image')
                if background not in (None, ""):
                    reference = decode_frame(background, '空桌参考图像无效，请重新记录。')
                changes,state,hint = change_candidates(image,reference,region,markers,result['obstacles'])
                result['generic_status'],result['generic_message'] = state,hint
                result['obstacles'] += project_obstacles(changes,result.get('homography'),layout)
                if state in ('ready','scene_changed'):
                    result['obstacle_status'] = 'ready'
            result['generic_obstacle_count'] = sum(obj.get('source')=='background_difference' for obj in result['obstacles'])
            result.update(proximity_monitor(markers,result['obstacles'],image.shape[1],image.shape[0]))
            result["processing_ms"] = round((time.perf_counter()-started)*1000, 1)
            self.json_response(200, result)
        except (ValueError, KeyError, TypeError, cv2.error) as error:
            self.json_response(400, {"error": str(error)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        OBSTACLE_DETECTOR = ObstacleDetector()
        print('桌面物品模型已载入。', flush=True)
    except (cv2.error, OSError) as error:
        OBSTACLE_ERROR = '目标检测模型未载入，请检查 models/yolox_s.onnx。'
        print(OBSTACLE_ERROR, str(error), flush=True)
    address = f"http://127.0.0.1:{args.port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        try:
            with urlopen(address+"/api/layout", timeout=2) as response:
                if response.headers.get("X-ArUco-Engine") != "local-v1":
                    raise ValueError("Another program is using this port.")
        except (OSError, ValueError):
            parser.exit(1, "此端口已被其他程序使用，请通过 --port 选择其他端口。\n")
        if args.open:
            webbrowser.open(address)
        parser.exit(0, f"定位台已运行：{address}\n")
    print(f"ArUco 定位台已启动 http://127.0.0.1:{args.port} ，关闭此终端结束服务。", flush=True)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
