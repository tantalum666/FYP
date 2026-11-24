"""Offline release checks. Inputs are synthetic, never physical accuracy evidence."""
import base64
from collections import Counter
import hashlib
import json
from io import BytesIO
from pathlib import Path
import sys
import tempfile
from threading import Thread
from unittest.mock import patch
from urllib.request import ProxyHandler, Request, build_opener

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
QA = Path(__file__).resolve().parent
DEMO = ROOT / 'research/2026-11-24-aruco-localisation/demo'
sys.path.insert(0, str(DEMO))
import aruco_demo as demo
import app
from monitoring import change_candidates, edge_monitor, proximity_monitor
from obstacles import ObstacleDetector
import download_model

dictionary = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
cfg = demo.read_layout(DEMO / 'layout.json')
capture = cv2.VideoCapture(str(DEMO / 'synthetic_input.avi'))
counts = Counter()
while True:
    ok, frame = capture.read()
    if not ok:
        break
    result = demo.locate(demo.detect(frame, dictionary), cfg)
    counts[result['status']] += 1
    if result['status'] != 'TRACKING':
        assert result['pose'] is None
capture.release()
assert counts == {'TRACKING': 45, 'TARGET_LOST': 5, 'WAITING_REFERENCES': 5, 'DUPLICATE_ID': 5}, counts

fixture = cv2.imread(str(QA / 'fixtures/l_shape_fixture.jpg'))
lcfg = demo.read_layout(QA / 'fixtures/l_shape_layout.json')
markers = demo.detect(fixture, dictionary)
located = demo.locate(markers, lcfg)
assert located['status'] == 'TRACKING' and located['reference_ids_used'] == [0, 1, 2]
assert np.linalg.norm(np.array(located['pose'][:2]) - [300, 150]) < 4
positions = demo.marker_positions(markers, located, lcfg)
assert positions[3]['table_mm'] is None
assert demo.locate([(i, c) for i, c in markers if i != 0], lcfg)['pose'] is None
assert demo.locate([(i, c) for i, c in markers if i != 4], lcfg)['status'] == 'TARGET_LOST'
assert demo.locate_image([(i, c) for i, c in markers if i == 4])['status'] == 'TRACKING'

polygon = np.float32([[80,80],[920,80],[920,620],[80,620]])
baseline = cv2.imread(str(QA / 'fixtures/empty.jpg'))
states = {}
for name, expected_edge, expected_near in [
    ('inside', 'INSIDE', 'FAR'), ('approach', 'INSIDE', 'NEAR_OBSTACLE'),
    ('overlap', 'INSIDE', 'OVERLAPPING'), ('near', 'NEAR_EDGE', 'FAR'),
    ('crossing', 'CROSSING_EDGE', 'FAR'), ('outside', 'OUTSIDE', 'FAR'),
    ('lost', 'TARGET_LOST', 'TARGET_LOST'),
]:
    image = cv2.imread(str(QA / f'fixtures/{name}.jpg'))
    tags = demo.detect(image, dictionary)
    result = demo.locate_image(tags)
    result['marker_positions'] = demo.marker_positions(tags, result, {})
    objects, status, _ = change_candidates(image, baseline, polygon, tags, [])
    assert status == 'ready' and len(objects) == 1
    assert objects[0]['confidence'] is None
    edge = edge_monitor(tags, result, polygon, 1000, 700)
    near = proximity_monitor(tags, objects, 1000, 700)
    assert edge['edge_status'] == expected_edge, (name, edge)
    assert near['proximity_status'] == expected_near, (name, near)
    states[name] = [edge['edge_status'], near['proximity_status']]

model = Path(sys.argv[1]) if len(sys.argv) > 1 else DEMO / 'models/yolox_s.onnx'
assert hashlib.sha256(model.read_bytes()).hexdigest() == 'c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063'
assert ObstacleDetector(model).detect(np.full((480,640,3), 255, np.uint8)) == []

with tempfile.TemporaryDirectory() as temporary:
    model_root = Path(temporary)
    (model_root / 'models').mkdir()
    payload = b'synthetic model transport fixture'
    source = {'url': 'https://huggingface.co/opencv/opencv_zoo/resolve/test/model',
              'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    (model_root / 'models/model-source.json').write_text(json.dumps(source))
    with patch.object(download_model, 'urlopen', return_value=BytesIO(payload)):
        downloaded = download_model.ensure_model(model_root)
    assert downloaded.read_bytes() == payload
    with patch.object(download_model, 'urlopen', side_effect=AssertionError('No repeat download')):
        assert download_model.ensure_model(model_root) == downloaded
    downloaded.write_bytes(b'previous file')
    with patch.object(download_model, 'urlopen', return_value=BytesIO(b'bad')):
        try:
            download_model.ensure_model(model_root)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid model accepted')
    assert downloaded.read_bytes() == b'previous file'
    assert not list((model_root / 'models').glob('*.part'))

# Exercise the shared HTTP handler without starting or accessing any camera.
server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}'
local_open = build_opener(ProxyHandler({})).open
try:
    for route in ['/', '/app.js', '/style.css', '/l_shape_guide.svg', '/api/layout']:
        with local_open(url + route, timeout=10) as response:
            assert response.status == 200 and response.read()
    _, encoded = cv2.imencode('.jpg', fixture)
    for mode in ['image', 'table']:
        data = {'coordinate_mode': mode, 'image': base64.b64encode(encoded).decode(), 'detect_objects': False}
        if mode == 'table':
            data['layout'] = lcfg
        request = Request(url + '/api/frame', json.dumps(data).encode(), {'Content-Type': 'application/json'})
        with local_open(request, timeout=10) as response:
            result = json.load(response)
            assert result['status'] == 'TRACKING'
            assert result['coordinate_units'] == ('px' if mode == 'image' else 'mm')
            if mode == 'image':
                assert all(item['table_mm'] is None for item in result['marker_positions'])
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)

report = {'date': '2026-11-24', 'synthetic_only': True, 'opencv': cv2.__version__,
          'four_reference_video_frames': dict(counts), 'l_shape_fixture': 'passed',
          'pixel_unit_isolation': 'passed', 'boundary_and_proximity': states,
          'model_sha_and_blank_inference': 'passed', 'shared_http_assets_and_modes': 'passed',
          'model_download_hash_reuse_and_invalid_download_preservation': 'passed',
          'physical_accuracy_tested': False, 'camera_accessed': False}
(QA / 'smoke-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
