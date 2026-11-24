#!/bin/zsh
cd "$(dirname "$0")"
for aruco_python in .venv/bin/python python3.12 python3.11 python3; do
  if "$aruco_python" -c 'import cv2; assert hasattr(cv2, "aruco")' >/dev/null 2>&1; then
    "$aruco_python" download_model.py || exit 1
    exec "$aruco_python" app.py --open
  fi
done
print '未找到 OpenCV 环境，请先按使用说明安装 requirements.txt。'
read 'aruco_reply?按回车关闭'
