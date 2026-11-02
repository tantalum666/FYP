import { useEffect, useRef, useState } from "react";
import { Camera, Mic, Square } from "lucide-react";
import { Modal } from "../../components/Dialogs";
import type { Translate } from "../../types";
import { LocalCapture } from "./localCapture";
import "./media-devices.css";

function deviceError(error: unknown, t: Translate) {
  const name = error instanceof Error ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return t(
      "Allow camera or microphone access for this site, then try again.",
      "请允许此网站使用摄像头或麦克风，然后重试。",
    );
  if (name === "NotFoundError")
    return t(
      "No device found. Connect one and try again.",
      "没有找到设备，请连接后重试。",
    );
  if (name === "NotReadableError")
    return t(
      "Another app may be using this device. Close it and try again.",
      "设备可能正被其他应用占用，关闭后重试。",
    );
  return t(
    "Could not use the device. Stop and try again.",
    "无法使用设备，请停止后重试。",
  );
}

export function MediaDevicePanel({
  t,
  onClose,
  voiceActive,
  canShare,
  provider,
  onShare,
}: {
  t: Translate;
  onClose: () => void;
  voiceActive: boolean;
  canShare: boolean;
  provider: string;
  onShare: (video: HTMLVideoElement) => void;
}) {
  const cameraCapture = useRef(new LocalCapture());
  const micCapture = useRef(new LocalCapture());
  const [camera, setCamera] = useState<MediaStream | null>(null);
  const [mic, setMic] = useState<MediaStream | null>(null);
  const [cameraPending, setCameraPending] = useState(false);
  const [micPending, setMicPending] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const meter = useRef<HTMLMeterElement>(null);
  const live = useRef(true);
  useEffect(() => {
    live.current = true;
    const stopHidden = () => {
      if (!document.hidden) return;
      cameraCapture.current.stop();
      micCapture.current.stop();
      setCamera(null);
      setMic(null);
      setCameraReady(false);
      setCameraPending(false);
      setMicPending(false);
    };
    document.addEventListener("visibilitychange", stopHidden);
    return () => {
      live.current = false;
      cameraCapture.current.stop();
      micCapture.current.stop();
      document.removeEventListener("visibilitychange", stopHidden);
    };
  }, []);
  useEffect(() => {
    const node = video.current;
    if (!node) return;
    node.srcObject = camera;
    if (camera)
      void node.play().catch(() => {
        if (live.current)
          setError(
            t(
              "Press Open camera again to preview.",
              "请重新打开摄像头以预览。",
            ),
          );
      });
    return () => {
      node.srcObject = null;
    };
  }, [camera, t]);
  useEffect(() => {
    if (!mic) return;
    const context = new AudioContext();
    const source = context.createMediaStreamSource(mic);
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser); // Deliberately not connected to speakers or a network.
    const samples = new Uint8Array(analyser.fftSize);
    let frame = 0;
    const update = () => {
      analyser.getByteTimeDomainData(samples);
      const energy =
        samples.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0) /
        samples.length;
      if (meter.current)
        meter.current.value = Math.min(1, Math.sqrt(energy) * 4);
      frame = requestAnimationFrame(update);
    };
    void context.resume().catch(() => {
      if (live.current)
        setError(
          t("Microphone audio could not start.", "无法开始麦克风音频检测。"),
        );
    });
    update();
    return () => {
      cancelAnimationFrame(frame);
      source.disconnect();
      analyser.disconnect();
      void context.close();
    };
  }, [mic, t]);
  function stopCamera() {
    cameraCapture.current.stop();
    setCamera(null);
    setCameraReady(false);
    setCameraPending(false);
    setSent(false);
  }
  function stopMic() {
    micCapture.current.stop();
    setMic(null);
    setMicPending(false);
  }
  async function startCamera() {
    setError("");
    setSent(false);
    setCameraPending(true);
    try {
      const stream = await cameraCapture.current.start({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (!stream || !live.current) return;
      stream.getVideoTracks().forEach((track) => {
        track.onended = () => {
          if (cameraCapture.current.owns(stream)) stopCamera();
        };
      });
      setCamera(stream);
    } catch (reason) {
      if (live.current) setError(deviceError(reason, t));
    } finally {
      if (live.current) setCameraPending(cameraCapture.current.pending);
    }
  }
  async function startMic() {
    setError("");
    setMicPending(true);
    try {
      const stream = await micCapture.current.start({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false,
      });
      if (!stream || !live.current) return;
      stream.getAudioTracks().forEach((track) => {
        track.onended = () => {
          if (micCapture.current.owns(stream)) stopMic();
        };
      });
      setMic(stream);
    } catch (reason) {
      if (live.current) setError(deviceError(reason, t));
    } finally {
      if (live.current) setMicPending(micCapture.current.pending);
    }
  }
  return (
    <Modal
      title={t("Camera & microphone", "摄像头与麦克风")}
      closeLabel={t("Close", "关闭")}
      onClose={onClose}
      className="media-device-dialog"
    >
      <p className="media-preview-note">
        {t(
          "Preview stays on this device until you choose to share a frame.",
          "预览留在本机，选择分享后才发送画面。",
        )}
      </p>
      <div className="media-camera-preview">
        <video
          ref={video}
          autoPlay
          muted
          playsInline
          hidden={!camera}
          onLoadedData={() => setCameraReady(true)}
          aria-label={t("Local camera preview", "本机摄像头预览")}
        />
        {!camera && <Camera size={34} aria-hidden="true" />}
      </div>
      <div className="workspace-inline-actions">
        {camera || cameraPending ? (
          <button className="secondary" onClick={stopCamera}>
            <Square size={16} />
            {t("Stop camera", "关闭摄像头")}
          </button>
        ) : (
          <button className="secondary" onClick={() => void startCamera()}>
            <Camera size={17} />
            {t("Open camera", "打开摄像头")}
          </button>
        )}
        <button
          className="primary"
          disabled={!cameraReady || !canShare}
          onClick={() => {
            if (
              !camera ||
              !video.current ||
              !canShare ||
              !cameraCapture.current.owns(camera)
            )
              return;
            try {
              onShare(video.current);
              setSent(true);
              setError("");
            } catch {
              setError(
                t(
                  "Start a voice conversation before sharing a frame.",
                  "开始语音对话后再分享画面。",
                ),
              );
            }
          }}
        >
          {t("Share this frame", "分享当前画面")}
        </button>
      </div>
      <p className="media-device-status" role="status">
        {cameraPending
          ? t("Waiting for camera access…", "等待摄像头许可…")
          : sent
            ? t("Frame sent to ", "画面已发送至 ") + provider
            : camera
              ? camera.getVideoTracks()[0]?.label
              : t("Camera off", "摄像头已关闭")}
      </p>
      {!canShare && (
        <p className="media-device-status">
          {t(
            "Start voice to share a frame with Alice.",
            "开始语音对话后可向 Alice 分享画面。",
          )}
        </p>
      )}
      <section className="media-mic-test">
        <div className="workspace-inline-actions">
          {mic || micPending ? (
            <button className="secondary" onClick={stopMic}>
              <Square size={16} />
              {t("Stop test", "停止检测")}
            </button>
          ) : (
            <button
              className="secondary"
              disabled={voiceActive}
              onClick={() => void startMic()}
            >
              <Mic size={17} />
              {t("Test microphone", "检测麦克风")}
            </button>
          )}
          <meter
            ref={meter}
            min={0}
            max={1}
            value={0}
            aria-label={t("Microphone input level", "麦克风输入音量")}
          />
        </div>
        <p className="media-device-status" role="status">
          {voiceActive
            ? t("Microphone is in the voice call.", "麦克风正在语音对话中。")
            : micPending
              ? t("Waiting for microphone access…", "等待麦克风许可…")
              : mic
                ? t("Listening locally · ", "本机检测中 · ") +
                  mic.getAudioTracks()[0]?.label
                : t(
                    "Local test only; no audio is saved or sent.",
                    "仅本机检测，不保存或发送音频。",
                  )}
        </p>
      </section>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
    </Modal>
  );
}
