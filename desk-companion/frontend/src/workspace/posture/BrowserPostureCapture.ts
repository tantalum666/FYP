import { request } from "../../api";
import { LocalCapture } from "../media/localCapture";

export type CameraState = {
  phase: "idle" | "starting" | "active" | "error";
  stream?: MediaStream;
  code?: string;
};

/** Owns one camera/worker/lease. No frame, recording or audio is sent to the API. */
export class BrowserPostureCapture {
  private capture = new LocalCapture();
  private worker: Worker | null = null;
  private video: HTMLVideoElement | null = null;
  private stopped = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private lease: string | null = null;
  private boot = "";
  private camera = "";
  private offset = 0;
  private sequence = 0;
  private lastFrame = -1;
  private unlock: () => void = () => {};
  private cancelModel: (() => void) | null = null;
  constructor(private onState: (state: CameraState) => void) {}

  async start(client: string, prompt: boolean) {
    const run = async () => {
      if (this.stopped) return;
      const released = new Promise<void>((resolve) => {
        this.unlock = resolve;
      });
      try {
        this.onState({ phase: "starting" });
        if (
          typeof Worker === "undefined" ||
          typeof OffscreenCanvas === "undefined" ||
          typeof createImageBitmap === "undefined"
        )
          throw new Error("POSTURE_DEVICE_UNSUPPORTED");
        if (!prompt && navigator.permissions) {
          const permission = await navigator.permissions
            .query({ name: "camera" as PermissionName })
            .catch(() => null);
          if (permission && permission.state !== "granted")
            throw new Error("POSTURE_CAMERA_PERMISSION");
        }
        if (this.stopped) return;
        await this.model();
        if (this.stopped) return;
        const stream = await this.capture.start({
          audio: false,
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: "user",
            frameRate: { ideal: 5, max: 10 },
          },
        });
        if (!stream || this.stopped) return;
        const track = stream.getVideoTracks()[0];
        const device = track.getSettings().deviceId || "default";
        const hash = await crypto.subtle.digest(
          "SHA-256",
          new TextEncoder().encode(device),
        );
        this.camera = `browser:${client}:${Array.from(new Uint8Array(hash))
          .map((x) => x.toString(16).padStart(2, "0"))
          .join("")
          .slice(0, 24)}`;
        if (this.stopped) return;
        this.video = document.createElement("video");
        this.video.muted = true;
        this.video.playsInline = true;
        this.video.srcObject = stream;
        await this.video.play();
        const before = Date.now();
        const admitted = await request<{
          lease: string;
          boot_id: string;
          server_time: string;
        }>("/posture/browser/session", {
          method: "POST",
          body: JSON.stringify({ client_id: client, camera_id: this.camera }),
        });
        this.lease = admitted.lease;
        if (this.stopped) {
          this.stop();
          return;
        }
        this.boot = admitted.boot_id;
        this.offset =
          Date.parse(admitted.server_time) - (before + Date.now()) / 2;
        track.onended = () => this.fail("POSTURE_CAMERA_ENDED");
        this.worker!.onmessage = ({ data }) => {
          if (data.type === "error") {
            this.fail(data.code);
            return;
          }
          if (data.type === "observation") void this.deliver(data.observation);
        };
        this.onState({ phase: "active", stream });
        void this.frame();
        await released;
      } catch (error) {
        if (!this.stopped)
          this.fail(
            error instanceof Error
              ? error.message
              : "POSTURE_CAMERA_UNAVAILABLE",
          );
      } finally {
        this.stop();
      }
    };
    if (navigator.locks) {
      await navigator.locks.request(
        "desk-local-posture-camera",
        { ifAvailable: true },
        async (lock) => {
          if (!lock) {
            this.fail("POSTURE_CAMERA_BUSY");
            return;
          }
          await run();
        },
      );
    } else await run();
  }

  private model() {
    return new Promise<void>((resolve, reject) => {
      const worker = new Worker(new URL("./pose.worker.ts", import.meta.url), {
        type: "module",
      });
      this.worker = worker;
      const deadline = setTimeout(
        () => reject(new Error("POSTURE_MODEL_UNAVAILABLE")),
        20000,
      );
      this.cancelModel = () => {
        clearTimeout(deadline);
        reject(new Error("POSTURE_CAPTURE_STOPPED"));
      };
      worker.onerror = () => {
        clearTimeout(deadline);
        reject(new Error("POSTURE_MODEL_UNAVAILABLE"));
      };
      worker.onmessage = ({ data }) => {
        clearTimeout(deadline);
        this.cancelModel = null;
        if (data.type === "ready") {
          worker.onerror = () => this.fail("POSTURE_MODEL_UNAVAILABLE");
          resolve();
        } else reject(new Error(data.code || "POSTURE_MODEL_UNAVAILABLE"));
      };
      worker.postMessage({
        type: "init",
        base: new URL("/posture-assets", location.href).href,
      });
    });
  }
  private async frame() {
    const video = this.video;
    if (this.stopped || !video || !this.worker) return;
    if (video.readyState < 2 || video.currentTime === this.lastFrame) {
      this.timer = setTimeout(() => void this.frame(), 250);
      return;
    }
    this.lastFrame = video.currentTime;
    const captured = Math.round(Date.now() + this.offset);
    try {
      const frame = await createImageBitmap(video);
      if (this.stopped) {
        frame.close();
        return;
      }
      this.worker.postMessage(
        { frame, captured, timestamp: performance.now() },
        [frame],
      );
    } catch {
      this.fail("POSTURE_CAMERA_UNAVAILABLE");
    }
  }
  private async deliver(observation: Record<string, unknown>) {
    if (this.stopped || !this.lease) return;
    try {
      await request("/posture/browser/observations", {
        method: "POST",
        body: JSON.stringify({
          lease: this.lease,
          batch: {
            source: "live",
            boot_id: this.boot,
            observations: [
              {
                ...observation,
                camera_id: this.camera,
                sequence: this.sequence++,
              },
            ],
          },
        }),
      });
      if (!this.stopped) this.timer = setTimeout(() => void this.frame(), 200);
    } catch (error) {
      this.fail(
        error instanceof Error ? error.message : "POSTURE_CONNECTION_LOST",
      );
    }
  }
  private fail(code: string) {
    if (this.stopped) return;
    this.onState({ phase: "error", code });
    this.stop();
  }
  stop() {
    this.stopped = true;
    this.cancelModel?.();
    this.cancelModel = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    this.worker?.terminate();
    this.worker = null;
    if (this.video) {
      this.video.pause();
      this.video.srcObject = null;
      this.video = null;
    }
    this.capture.stop();
    if (this.lease) {
      const lease = this.lease;
      this.lease = null;
      void request(`/posture/browser/session/${lease}`, {
        method: "DELETE",
      }).catch(() => {});
    }
    this.unlock();
  }
}
