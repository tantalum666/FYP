import type { Translate } from "../../types";
import { validCapacityDimension } from "./workCapacity.ts";
import type { WorkCapacity } from "./workCapacity.ts";
export const captureStates = [
  "review",
  "queued",
  "fetching",
  "publishing",
  "verified",
  "expired",
  "failed",
  "cancelled",
  "unknown",
] as const;
export type CaptureState = (typeof captureStates)[number];
export interface CaptureAcquisition {
  total_lines: number;
  capture_id: string;
  url: string;
  received_at: string;
  http_status: 200;
  response_mime: "text/plain" | "text/markdown" | "text/html";
  response_charset: "utf-8";
  raw_sha256: string;
  raw_byte_count: number;
  extracted_sha256: string;
  extracted_byte_count: number;
  extractor_version: "static_text_v1";
  coverage: "complete_accepted_static_extraction";
  raw_retained: false;
  rendered_coverage: "unknown";
}
export interface PublicCapture {
  id: string;
  state: CaptureState;
  version: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
  dispatch_possible: boolean;
  error_code: string | null;
  cancel_available: boolean;
  url?: string;
  label?: string | null;
  display_name?: string;
  intent_hash?: string;
  source_id?: string | null;
  source_status?: "not_reserved" | "unknown" | "verified";
  acquisition?: CaptureAcquisition | null;
}
export interface CaptureReview {
  id: string;
  version: number;
  state: "review";
  intent_hash: string;
  expires_at: string;
  url: string;
  host: string;
  label: string | null;
  display_name: string;
  method: "GET";
  public_only: true;
  credentials: "none";
  redirects: "deny";
  policy_version: 1;
  extractor_version: "static_text_v1";
  retention: "local_indefinite_no_delete_control";
  raw_retention: "none";
  source_capacity: WorkCapacity["sources"];
  history_used: number;
  history_limit: 200;
  observed_at: string;
  advisory: true;
  untrusted: true;
  starts_work: false;
  grants_model_sharing: false;
}
export const captureObject = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const text = (v: unknown, max: number): v is string =>
  typeof v === "string" &&
  v.length > 0 &&
  v.length <= max &&
  !/[\u0000-\u001f\u007f-\u009f]/.test(v);
const int = (v: unknown, max = Number.MAX_SAFE_INTEGER): v is number =>
  typeof v === "number" && Number.isSafeInteger(v) && v >= 1 && v <= max;
export const captureId = (v: unknown): v is string =>
  typeof v === "string" && /^[a-f0-9]{32}$/.test(v);
const hash = (v: unknown): v is string =>
  typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const time = (v: unknown): v is string =>
  typeof v === "string" &&
  /^\d{4}-\d\d-\d\dT[^\s]{1,40}(Z|\+00:00)$/.test(v) &&
  Number.isFinite(Date.parse(v));
export function captureUrl(v: unknown): v is string {
  if (typeof v !== "string" || v.length > 1024) return false;
  const match = /^https:\/\/([a-z0-9.-]+)(\/[A-Za-z0-9/_~.\-]*)$/.exec(v);
  if (!match || match[1].length > 253 || !/[a-z]/.test(match[1])) return false;
  const labels = match[1].split(".");
  return (
    labels.length >= 2 &&
    labels.every((x) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(x)) &&
    !match[2].includes("//") &&
    !match[2].split("/").some((x) => x === "." || x === "..")
  );
}
export function validCaptureAcquisition(v: unknown): v is CaptureAcquisition {
  return (
    captureObject(v) &&
    captureId(v.capture_id) &&
    int(v.total_lines, 24576) &&
    captureUrl(v.url) &&
    time(v.received_at) &&
    v.http_status === 200 &&
    ["text/plain", "text/markdown", "text/html"].includes(
      String(v.response_mime),
    ) &&
    v.response_charset === "utf-8" &&
    hash(v.raw_sha256) &&
    int(v.raw_byte_count, 131072) &&
    hash(v.extracted_sha256) &&
    int(v.extracted_byte_count, 24576) &&
    v.extractor_version === "static_text_v1" &&
    v.coverage === "complete_accepted_static_extraction" &&
    v.raw_retained === false &&
    v.rendered_coverage === "unknown"
  );
}
const scalarKeys = [
  "id",
  "state",
  "version",
  "created_at",
  "updated_at",
  "expires_at",
  "dispatch_possible",
  "error_code",
  "cancel_available",
];
export function validPublicCapture(
  v: unknown,
  hidden: boolean,
): v is PublicCapture {
  if (
    !captureObject(v) ||
    !captureId(v.id) ||
    !captureStates.includes(v.state as CaptureState) ||
    !int(v.version) ||
    !time(v.created_at) ||
    !time(v.updated_at) ||
    !time(v.expires_at) ||
    typeof v.dispatch_possible !== "boolean" ||
    typeof v.cancel_available !== "boolean" ||
    !(
      v.error_code === null ||
      (typeof v.error_code === "string" &&
        /^[A-Z][A-Z0-9_]{0,79}$/.test(v.error_code))
    )
  )
    return false;
  if (hidden) return Object.keys(v).every((k) => scalarKeys.includes(k));
  return (
    captureUrl(v.url) &&
    (v.label === null || text(v.label, 120)) &&
    v.display_name === `capture-${v.id}.txt` &&
    hash(v.intent_hash) &&
    (v.source_id === null || captureId(v.source_id)) &&
    (v.source_status !== "not_reserved" || v.source_id === null) &&
    ["not_reserved", "unknown", "verified"].includes(String(v.source_status)) &&
    (v.acquisition === null ||
      (validCaptureAcquisition(v.acquisition) &&
        v.acquisition.capture_id === v.id &&
        v.acquisition.url === v.url)) &&
    (v.source_status !== "verified" ||
      (v.source_id !== null && v.acquisition !== null))
  );
}
export function validCaptureReview(
  v: unknown,
  capture: PublicCapture,
): v is CaptureReview {
  if (
    !captureObject(v) ||
    !captureUrl(capture.url) ||
    v.id !== capture.id ||
    v.version !== capture.version ||
    v.state !== "review" ||
    capture.state !== "review" ||
    v.intent_hash !== capture.intent_hash ||
    v.expires_at !== capture.expires_at ||
    v.url !== capture.url ||
    v.label !== capture.label ||
    v.display_name !== capture.display_name ||
    v.host !== new URL(capture.url!).hostname
  )
    return false;
  const c = v.source_capacity;
  return (
    v.capture_id === capture.id &&
    v.intent_version === 1 &&
    v.disclosure_version === 1 &&
    v.retain_capture_record === true &&
    v.destination === capture.url &&
    v.method === "GET" &&
    v.public_only === true &&
    v.credentials === "none" &&
    v.redirects === "deny" &&
    v.policy_version === 1 &&
    v.extractor_version === "static_text_v1" &&
    v.retention === "local_indefinite_no_delete_control" &&
    v.raw_retention === "none" &&
    captureObject(c) &&
    validCapacityDimension(c.count) &&
    c.count.limit === 100 &&
    validCapacityDimension(c.bytes) &&
    c.bytes.limit === 67108864 &&
    int(c.file_bytes) &&
    int(v.history_used, 200) &&
    v.history_limit === 200 &&
    time(v.observed_at) &&
    v.advisory === true &&
    v.untrusted === true &&
    v.starts_work === false &&
    v.grants_model_sharing === false
  );
}
export function captureDenial(error: unknown) {
  return (
    captureObject(error) &&
    (error.status === 401 ||
      error.status === 403 ||
      (typeof error.code === "string" &&
        /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN|CONTEXT_CHANGED/.test(
          error.code,
        )))
  );
}
export function captureError(error: unknown, t: Translate) {
  const code = captureObject(error) ? error.code : null;
  if (captureDenial(error))
    return t(
      "Access changed. Reopen Work with a current owner session; old approval cannot continue.",
      "访问权限已变化。请使用当前拥有者会话重新打开工作；旧批准不能继续。",
    );
  if (code === "CONNECTION_LOST")
    return t(
      "The response was lost. Inspect the original capture or retry only the pinned original operation. A new capture could reserve another source.",
      "响应丢失。请检查原采集记录，或仅重试已固定的原操作。新采集可能再占一个来源位置。",
    );
  return t(
    "The capture could not be confirmed. Refresh its saved status or reconcile locally before preparing another request. No automatic network retry is made.",
    "未能确认采集结果。请先刷新已保存状态或进行本地核验，再准备另一请求。不会自动重试网络请求。",
  );
}
export function captureStateLabel(state: CaptureState, t: Translate) {
  const labels: Record<CaptureState, [string, string]> = {
    review: ["Awaiting review", "等待审阅"],
    queued: ["Approved", "已批准"],
    fetching: ["Reading public page", "读取公开页面"],
    publishing: ["Saving extraction", "保存提取内容"],
    verified: ["Source verified", "来源已核验"],
    expired: ["Expired", "已到期"],
    failed: ["Failed", "失败"],
    cancelled: ["Cancelled", "已取消"],
    unknown: ["Outcome unknown", "结果未知"],
  };
  return t(...labels[state]);
}

/** Browser-side review lifetime supplements, never replaces, the server's authority clocks. */
export class CaptureReviewWindow {
  private readonly wallStart: number;
  private readonly monotonicStart: number;
  private readonly wallDeadline: number;
  private readonly monotonicDeadline: number;
  private expired = false;
  constructor(
    expiresAt: string,
    wall = Date.now(),
    monotonic = performance.now(),
  ) {
    this.wallStart = wall;
    this.monotonicStart = monotonic;
    this.wallDeadline = Math.min(Date.parse(expiresAt), wall + 300_000);
    this.monotonicDeadline = monotonic + Math.max(0, this.wallDeadline - wall);
  }
  remaining(wall = Date.now(), monotonic = performance.now()) {
    if (
      !Number.isFinite(wall) ||
      !Number.isFinite(monotonic) ||
      wall < this.wallStart ||
      monotonic < this.monotonicStart ||
      wall >= this.wallDeadline ||
      monotonic >= this.monotonicDeadline
    )
      this.expired = true;
    return this.expired
      ? 0
      : Math.max(
          0,
          Math.min(
            this.wallDeadline - wall,
            this.monotonicDeadline - monotonic,
          ),
        );
  }
}
