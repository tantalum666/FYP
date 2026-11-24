"""Desktop-object inference using the Apache-2.0 OpenCV Zoo YOLOX model.

Preprocessing and output decoding follow the upstream OpenCV Zoo example.
This adapter adds class selection, frame clipping and planar map projections.
"""
from pathlib import Path
from threading import Lock

import cv2
import numpy as np


MODEL = Path(__file__).with_name('models') / 'yolox_s.onnx'
DESKTOP_CLASSES = {
    39: ('bottle', '水瓶'), 40: ('wine glass', '高脚杯'), 41: ('cup', '水杯'),
    42: ('fork', '叉子'), 43: ('knife', '餐刀'), 44: ('spoon', '勺子'), 45: ('bowl', '碗'),
    58: ('potted plant', '盆栽'), 62: ('tv', '显示器'), 63: ('laptop', '笔记本电脑'),
    64: ('mouse', '鼠标'), 65: ('remote', '遥控器'), 66: ('keyboard', '键盘'),
    67: ('cell phone', '手机'), 73: ('book', '书本'), 75: ('vase', '花瓶'),
    76: ('scissors', '剪刀'),
}


class ObstacleDetector:
    def __init__(self, model=MODEL):
        self.net = cv2.dnn.readNetFromONNX(str(model))
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.lock = Lock()
        grids, strides = [], []
        for stride in (8, 16, 32):
            x, y = np.meshgrid(np.arange(640//stride), np.arange(640//stride))
            grid = np.stack((x, y), axis=2).reshape(-1, 2)
            grids.append(grid)
            strides.append(np.full((len(grid), 1), stride))
        self.grid = np.concatenate(grids)
        self.strides = np.concatenate(strides)

    def detect(self, image, confidence=.4):
        height, width = image.shape[:2]
        scale = min(640/width, 640/height)
        resized = cv2.resize(image, (int(width*scale), int(height*scale)))
        padded = np.full((640, 640, 3), 114, np.float32)
        padded[:resized.shape[0], :resized.shape[1]] = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        blob = padded.transpose(2, 0, 1)[None]
        with self.lock:
            self.net.setInput(blob)
            predictions = self.net.forward()[0].copy()
        predictions[:, :2] = (predictions[:, :2]+self.grid)*self.strides
        predictions[:, 2:4] = np.exp(predictions[:, 2:4])*self.strides
        scores = predictions[:, 4:5]*predictions[:, 5:]
        classes = scores.argmax(axis=1)
        values = scores.max(axis=1)
        selected = np.isin(classes, list(DESKTOP_CLASSES)) & (values >= confidence)
        predictions, classes, values = predictions[selected], classes[selected], values[selected]
        if not len(predictions):
            return []
        boxes = predictions[:, :4]/scale
        boxes[:, :2] -= boxes[:, 2:4]/2
        keep = cv2.dnn.NMSBoxesBatched(boxes.tolist(), values.tolist(), classes.tolist(), confidence, .45)
        result = []
        for index in np.asarray(keep).reshape(-1):
            x, y, w, h = boxes[index]
            x1, y1, x2, y2 = np.clip([x, y, x+w, y+h], [0, 0, 0, 0], [width, height, width, height])
            if x2 <= x1 or y2 <= y1:
                continue
            class_id = int(classes[index])
            name, label = DESKTOP_CLASSES[class_id]
            result.append({'class_id':class_id, 'name':name, 'label':label,
                           'confidence':round(float(values[index]), 4),
                           'box_px':[round(float(v), 1) for v in (x1,y1,x2,y2)],
                           'table_polygon_mm':None})
        return sorted(result, key=lambda item: item['confidence'], reverse=True)


def project_obstacles(objects, homography, layout):
    """Project image boxes onto the calibrated plane as an approximate region."""
    if homography is None:
        return objects
    transform = np.array(homography, dtype=np.float64)
    table = np.float32([[0,0],[layout['table_width_mm'],0],
                        [layout['table_width_mm'],layout['table_depth_mm']],
                        [0,layout['table_depth_mm']]])
    for obj in objects:
        x1,y1,x2,y2 = obj['box_px']
        box = np.float32([[[x1,y1],[x2,y1],[x2,y2],[x1,y2]]])
        projected = cv2.perspectiveTransform(box, transform)[0]
        if not np.isfinite(projected).all() or not cv2.isContourConvex(projected):
            continue
        area, clipped = cv2.intersectConvexConvex(projected, table)
        if area > 0 and clipped is not None:
            obj['table_polygon_mm'] = np.round(clipped.reshape(-1,2),1).tolist()
    return objects
