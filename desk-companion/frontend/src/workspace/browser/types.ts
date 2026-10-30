export interface BrowserSource {
  id: string;
  url: string;
  label: string;
}
export interface BrowserCapabilities {
  configured: boolean;
  ready: boolean;
  reason: string | null;
  experimental: true;
  scope: "public_synthetic_only";
  network_boundary: string;
  live_acceptance: string;
  destination: { id: string; url: string };
  sources: BrowserSource[];
  limits: Record<string, number | string | boolean>;
}
export interface BrowserObservation {
  id: string;
  source_id: string;
  url: string;
  title: string;
  heading: string;
  excerpt: string;
  sha256: string;
  observed_at: string;
  version: number;
}
export type BrowserJobState =
  | "review"
  | "queued"
  | "running"
  | "verifying"
  | "succeeded"
  | "failed"
  | "cancelling"
  | "cancelled"
  | "expired"
  | "unknown";
export interface BrowserJob {
  id: string;
  state: BrowserJobState;
  version: number;
  intent_hash?: string;
  request?: {
    source: BrowserObservation;
    title: string;
    document_name: string;
    content: string;
    destination: "https://stackedit.io/app";
    public_only: boolean;
    adapter: "stackedit_markdown_v1";
    catalog_version: number;
    environment_id: string;
  };
  expires_at: string;
  created_at: string;
  cancel_requested: boolean;
  cleanup_confirmed?: boolean;
  error: string | null;
  history?: { at: string; state: BrowserJobState; code: string | null }[];
  result?: {
    verified: boolean;
    byte_count?: number;
    sha256?: string;
    artifact_id?: string | null;
    browser_close_confirmed?: boolean;
    process_cleanup_confirmed?: boolean;
    export_method?: string;
    browser_version?: string;
    network_boundary?: string;
    data_scope?: string;
    [key: string]: unknown;
  } | null;
}

export function browserReady(
  capability: BrowserCapabilities | null,
  fresh: boolean,
) {
  return (
    fresh &&
    capability?.configured === true &&
    capability.ready === true &&
    capability.scope === "public_synthetic_only" &&
    capability.destination?.id === "stackedit_markdown_v1" &&
    capability.destination.url === "https://stackedit.io/app"
  );
}
export function browserReviewable(
  job: BrowserJob,
  ready: boolean,
  now: number,
) {
  return (
    ready &&
    job.state === "review" &&
    job.request?.public_only === true &&
    job.request.destination === "https://stackedit.io/app" &&
    job.request.adapter === "stackedit_markdown_v1" &&
    !!job.request.content &&
    !!job.request.document_name &&
    !!job.intent_hash &&
    /^[a-f0-9]{64}$/.test(job.intent_hash) &&
    Date.parse(job.expires_at) > now &&
    !job.cancel_requested
  );
}
export function browserCancellable(job: BrowserJob) {
  return (
    ["review", "queued", "running", "verifying", "unknown"].includes(
      job.state,
    ) && !job.cancel_requested
  );
}
export function browserVerified(job: BrowserJob) {
  return (
    job.state === "succeeded" &&
    job.cleanup_confirmed === true &&
    job.result?.process_cleanup_confirmed === true &&
    job.result.browser_close_confirmed === true &&
    browserExportVerified(job)
  );
}
export function browserExportVerified(job: BrowserJob) {
  return (
    ["succeeded", "unknown"].includes(job.state) &&
    job.result?.verified === true &&
    job.result.export_method === "stackedit_ui_markdown_download" &&
    typeof job.result.byte_count === "number" &&
    job.result.byte_count > 0 &&
    job.result.byte_count <= 65536 &&
    typeof job.result.sha256 === "string" &&
    /^[a-f0-9]{64}$/.test(job.result.sha256)
  );
}
export function browserSelection(
  current: string | null,
  next: string | null,
  dirty: boolean,
  locked: boolean,
) {
  if (current === next || locked) return "stay";
  return dirty ? "confirm" : "switch";
}
/** Do not turn unexpected server/source strings into navigable URLs. */
export function catalogUrl(url: string, sources: BrowserSource[]) {
  return sources.some((source) => source.url === url) &&
    /^https:\/\/[^/?#@]+\//.test(url)
    ? url
    : null;
}
