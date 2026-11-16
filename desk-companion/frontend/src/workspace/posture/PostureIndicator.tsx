import { Camera } from "lucide-react";
import type { Translate } from "../../types";
import { write } from "../../api";
import { usePostureCapture } from "./PostureCaptureContext";

export function PostureIndicator({ t }: { t: Translate }) {
  const camera = usePostureCapture();
  if (camera.state.phase !== "active") return null;
  const label = t(
    "Local posture observation is on — pause",
    "本地坐姿观察中，点击暂停",
  );
  return (
    <button
      className="alice-posture-indicator"
      title={label}
      aria-label={label}
      onClick={() => {
        camera.disable();
        void write("/posture/actions", { action: "pause" }).catch(() => {});
      }}
    >
      <Camera size={14} />
    </button>
  );
}
