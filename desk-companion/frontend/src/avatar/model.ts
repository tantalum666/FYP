import type { WorkspaceSnapshot } from "../workspace/types.ts";

export type AvatarState =
  | "idle"
  | "listening"
  | "speaking"
  | "thinking"
  | "confirm"
  | "connecting"
  | "alert"
  | "disconnected";
export const SAMPLE_MODEL = "/avatars/pixiv-sample.vrm";
export const MAX_MODEL_BYTES = 25 * 1024 * 1024;
export interface PlaybackSample {
  level: number;
  at: number;
}

export function playbackLevel(sample: PlaybackSample | null, now = Date.now()) {
  if (
    !sample ||
    !Number.isFinite(sample.level) ||
    !Number.isFinite(sample.at) ||
    sample.at > now + 100 ||
    now - sample.at > 300
  )
    return 0;
  return Math.max(0, Math.min(1, sample.level));
}

export function rmsLevel(values: Float32Array) {
  if (!values.length) return 0;
  let sum = 0;
  for (const value of values) {
    if (!Number.isFinite(value)) return 0;
    sum += value * value;
  }
  const rms = Math.sqrt(sum / values.length);
  return Math.max(0, Math.min(1, (rms - 0.008) * 7));
}

export function assistantState(
  data: WorkspaceSnapshot | null,
  unavailable: boolean,
  now = Date.now() / 1000,
): AvatarState {
  if (unavailable || !data) return "disconnected";
  if (data.voice.active) {
    const state = data.voice.state;
    return [
      "listening",
      "speaking",
      "thinking",
      "confirm",
      "connecting",
    ].includes(state)
      ? (state as AvatarState)
      : "idle";
  }
  const posture = data.posture,
    feedback = posture.feedback;
  if (
    posture.connected &&
    posture.preferences.enabled &&
    !posture.paused &&
    now >= posture.snooze_until &&
    feedback?.outcome === "waiting" &&
    feedback.source === "live" &&
    now >= feedback.created_at &&
    now - feedback.created_at < 30
  )
    return "alert";
  return "idle";
}

// VRM is a binary glTF. Only self-contained files are accepted, so a model
// cannot make the browser fetch arbitrary texture or buffer URLs.
export function inspectVrm(bytes: ArrayBuffer) {
  if (bytes.byteLength > MAX_MODEL_BYTES || bytes.byteLength < 20)
    throw new Error("MODEL_SIZE");
  const view = new DataView(bytes);
  if (
    view.getUint32(0, true) !== 0x46546c67 ||
    view.getUint32(4, true) !== 2 ||
    view.getUint32(8, true) !== bytes.byteLength ||
    view.getUint32(16, true) !== 0x4e4f534a
  )
    throw new Error("MODEL_FORMAT");
  const length = view.getUint32(12, true);
  if (length > bytes.byteLength - 20 || length > 4 * 1024 * 1024)
    throw new Error("MODEL_FORMAT");
  const json = JSON.parse(
    new TextDecoder().decode(new Uint8Array(bytes, 20, length)),
  );
  if (!json.extensions?.VRMC_vrm && !json.extensions?.VRM)
    throw new Error("MODEL_NOT_VRM");
  for (const resource of [...(json.images ?? []), ...(json.buffers ?? [])]) {
    if (resource.uri !== undefined) throw new Error("MODEL_EXTERNAL_RESOURCE");
  }
  // The supported loader path needs no remote codecs or unknown extensions.
  const supported = new Set([
    "VRMC_vrm",
    "VRMC_springBone",
    "VRMC_node_constraint",
    "VRMC_materials_mtoon",
    "VRMC_materials_hdr_emissiveMultiplier",
    "VRMC_materials_constraint",
    "KHR_materials_unlit",
    "KHR_texture_transform",
  ]);
  supported.add("VRM");
  if (
    (json.extensionsRequired ?? []).some((name: string) => !supported.has(name))
  )
    throw new Error("MODEL_EXTENSION");
  const meta = json.extensions.VRMC_vrm?.meta ?? json.extensions.VRM?.meta;
  return {
    name: String(meta?.name ?? meta?.title ?? "Local VRM").slice(0, 100),
    meta,
  };
}
