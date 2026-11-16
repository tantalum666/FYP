import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

let detector: PoseLandmarker | null = null;
const light = new OffscreenCanvas(64, 48);
const pixels = light.getContext("2d", { willReadFrequently: true })!;
const names = [
  [0, "nose"],
  [7, "left_ear"],
  [8, "right_ear"],
  [11, "left_shoulder"],
  [12, "right_shoulder"],
] as const;
self.onmessage = async ({ data }) => {
  if (data.type === "init") {
    try {
      const files = await FilesetResolver.forVisionTasks(
        `${data.base}/wasm`,
        true,
      );
      detector = await PoseLandmarker.createFromOptions(files, {
        baseOptions: {
          modelAssetPath: `${data.base}/pose_landmarker_lite.task`,
          delegate: "CPU",
        },
        runningMode: "VIDEO",
        numPoses: 2,
        minPoseDetectionConfidence: 0.6,
        minPosePresenceConfidence: 0.6,
        minTrackingConfidence: 0.6,
      });
      self.postMessage({ type: "ready" });
    } catch {
      self.postMessage({ type: "error", code: "POSTURE_MODEL_UNAVAILABLE" });
    }
    return;
  }
  const bitmap: ImageBitmap = data.frame;
  if (!bitmap) return;
  try {
    if (!detector) throw new Error("not ready");
    pixels.drawImage(bitmap, 0, 0, 64, 48);
    const image = pixels.getImageData(0, 0, 64, 48).data;
    let brightness = 0;
    for (let i = 0; i < image.length; i += 4)
      brightness +=
        image[i] * 0.299 + image[i + 1] * 0.587 + image[i + 2] * 0.114;
    const result = detector.detectForVideo(bitmap, data.timestamp);
    const landmarks: Record<
      string,
      { x: number; y: number; visibility: number; presence: number }
    > = {};
    if (result.landmarks.length === 1)
      for (const [index, name] of names) {
        const p = result.landmarks[0][index];
        if (
          p &&
          Number.isFinite(p.x) &&
          Number.isFinite(p.y) &&
          p.x >= -0.2 &&
          p.x <= 1.2 &&
          p.y >= -0.2 &&
          p.y <= 1.2
        )
          landmarks[name] = {
            x: p.x,
            y: p.y,
            visibility: p.visibility ?? 0,
            presence: p.presence ?? p.visibility ?? 0,
          };
      }
    self.postMessage({
      type: "observation",
      observation: {
        captured_ms: data.captured,
        frame_width: bitmap.width,
        frame_height: bitmap.height,
        person_count: result.landmarks.length,
        brightness: brightness / (64 * 48),
        landmarks,
      },
    });
  } catch {
    self.postMessage({ type: "error", code: "POSTURE_MODEL_UNAVAILABLE" });
  } finally {
    bitmap.close();
  }
};
