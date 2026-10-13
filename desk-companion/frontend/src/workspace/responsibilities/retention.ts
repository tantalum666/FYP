import type { Responsibility, WatchDetail } from "./types";
export type RetentionAction = "trash" | "restore" | "purge";
export interface WatchMaintenanceUsage {
  version: 1;
  retained_count: number | null;
  trashed_count: number | null;
  lifetime_count: number | null;
  lifetime_limit: 256;
  lifetime_remaining: number | null;
  state: "known" | "over_limit" | "unavailable";
}
export interface RetentionPreview {
  kind: "watch_retention_preview";
  preview_id: string;
  action: RetentionAction;
  responsibility: Pick<
    Responsibility,
    "id" | "title" | "status" | "version"
  > & {
    title: string;
    retention_state: "retained" | "trashed";
    retention_version: number;
  };
  counts: {
    definitions: 1;
    source_baselines: number;
    retained_reviews: number;
    operation_receipts: number;
  };
  retained_operation_receipts_after: number;
  logical_slots_released: 0 | 1;
  receipts_retained: true;
  independent_tasks_retained: true;
  independent_work_retained: true;
  expires_at: string;
  maintenance_usage: WatchMaintenanceUsage;
  revision: number;
}
export interface RetentionDisposition {
  kind: "retention_disposition";
  responsibility_id: string;
  retention_state: "trashed" | "purged";
  retention_version: number;
  original_operation_kind: string;
  review_id: string | null;
  operation_id: string;
  revision: number;
  recorded_success: true;
}
export type WatchMutationResult =
  | RetentionDisposition
  | {
      responsibility: Responsibility;
      saved: true;
      operation_id: string;
      revision: number;
      review_id?: string;
      acknowledged?: true;
    };
export interface MaintenanceList {
  responsibilities: Responsibility[];
  maintenance_usage: WatchMaintenanceUsage;
  revision: number;
  server_time: string;
}
const object = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const integer = (v: unknown): v is number =>
  typeof v === "number" && Number.isSafeInteger(v) && v >= 0;
const positive = (v: unknown): v is number => integer(v) && v > 0;
const id = (v: unknown): v is string =>
  typeof v === "string" && v.length > 0 && v.length <= 160;
const timestamp = (v: unknown): v is string =>
  typeof v === "string" &&
  /^\d{4}-\d\d-\d\dT.*(?:Z|\+00:00)$/.test(v) &&
  Number.isFinite(Date.parse(v));
export const terminalWatch = (status: string) =>
  ["cancelled", "expired", "budget_exhausted"].includes(status);
export function validMaintenanceUsage(v: unknown): v is WatchMaintenanceUsage {
  if (!object(v) || v.version !== 1 || v.lifetime_limit !== 256) return false;
  if (v.state === "unavailable" || v.state === "over_limit")
    return [
      v.retained_count,
      v.trashed_count,
      v.lifetime_count,
      v.lifetime_remaining,
    ].every((n) => n === null);
  return (
    v.state === "known" &&
    integer(v.retained_count) &&
    v.retained_count <= 20 &&
    integer(v.trashed_count) &&
    v.trashed_count <= v.retained_count &&
    integer(v.lifetime_count) &&
    v.lifetime_count >= v.retained_count &&
    v.lifetime_count <= 256 &&
    v.lifetime_remaining === 256 - v.lifetime_count
  );
}
export function validMaintenanceRow(v: unknown): v is Responsibility {
  return (
    object(v) &&
    id(v.id) &&
    typeof v.title === "string" &&
    v.title.length <= 160 &&
    positive(v.version) &&
    positive(v.retention_version) &&
    (v.retention_state === "retained" || v.retention_state === "trashed") &&
    typeof v.status === "string" &&
    terminalWatch(v.status) &&
    v.hidden === false &&
    Array.isArray(v.task_ids) &&
    v.task_ids.length <= 10 &&
    v.task_ids.every(id) &&
    Array.isArray(v.fields) &&
    integer(v.review_budget) &&
    integer(v.reviews_used)
  );
}
export function validMaintenanceList(v: unknown): v is MaintenanceList {
  return (
    object(v) &&
    Array.isArray(v.responsibilities) &&
    v.responsibilities.length <= 20 &&
    v.responsibilities.every(
      (r) => validMaintenanceRow(r) && r.retention_state === "trashed",
    ) &&
    new Set(v.responsibilities.map((r) => r.id)).size ===
      v.responsibilities.length &&
    validMaintenanceUsage(v.maintenance_usage) &&
    (v.maintenance_usage.trashed_count === null ||
      v.responsibilities.length === v.maintenance_usage.trashed_count) &&
    integer(v.revision) &&
    timestamp(v.server_time)
  );
}
export function validMaintenanceDetail(
  v: unknown,
  expectedId: string,
): v is WatchDetail {
  return (
    object(v) &&
    validMaintenanceRow(v.responsibility) &&
    v.responsibility.id === expectedId &&
    integer(v.revision) &&
    Array.isArray(v.reviews) &&
    v.reviews.length <= 51 &&
    v.reviews.every(
      (r) =>
        object(r) &&
        id(r.id) &&
        r.responsibility_id === expectedId &&
        positive(r.version) &&
        Array.isArray(r.changed_fields) &&
        Array.isArray(r.changed_ids) &&
        typeof r.delivery_state === "string",
    ) &&
    Array.isArray(v.selected_tasks) &&
    v.selected_tasks.length <= 10 &&
    v.selected_tasks.every(
      (t) =>
        object(t) &&
        id(t.id) &&
        typeof t.title === "string" &&
        typeof t.available === "boolean",
    )
  );
}
export function validRetentionPreview(
  v: unknown,
  row: Responsibility,
  action: RetentionAction,
): v is RetentionPreview {
  if (
    !object(v) ||
    v.kind !== "watch_retention_preview" ||
    !id(v.preview_id) ||
    v.action !== action ||
    !object(v.responsibility) ||
    !object(v.counts)
  )
    return false;
  const r = v.responsibility,
    c = v.counts;
  return (
    r.id === row.id &&
    r.version === row.version &&
    r.retention_version === row.retention_version &&
    r.retention_state === row.retention_state &&
    typeof r.title === "string" &&
    r.title === row.title &&
    r.status === row.status &&
    terminalWatch(String(r.status)) &&
    (action === "restore"
      ? r.retention_state === "trashed"
      : action === "trash"
        ? r.retention_state === "retained"
        : true) &&
    c.definitions === 1 &&
    integer(c.source_baselines) &&
    c.source_baselines <= 10 &&
    c.source_baselines === row.task_ids?.length &&
    integer(c.retained_reviews) &&
    c.retained_reviews <= 51 &&
    integer(c.operation_receipts) &&
    c.operation_receipts <= 258 &&
    v.retained_operation_receipts_after === c.operation_receipts + 1 &&
    v.logical_slots_released === (action === "purge" ? 1 : 0) &&
    v.receipts_retained === true &&
    v.independent_tasks_retained === true &&
    v.independent_work_retained === true &&
    timestamp(v.expires_at) &&
    validMaintenanceUsage(v.maintenance_usage) &&
    integer(v.revision)
  );
}
export function validWatchMutationResult(
  v: unknown,
  expectedId?: string,
  expectedOperation?: string,
  expectedKind?: string,
): v is WatchMutationResult {
  if (
    !object(v) ||
    !id(v.operation_id) ||
    (expectedOperation && v.operation_id !== expectedOperation) ||
    !integer(v.revision)
  )
    return false;
  if (v.kind === "retention_disposition") {
    const keys = [
      "kind",
      "responsibility_id",
      "retention_state",
      "retention_version",
      "original_operation_kind",
      "review_id",
      "operation_id",
      "revision",
      "recorded_success",
    ];
    return (
      Object.keys(v).every((k) => keys.includes(k)) &&
      id(v.responsibility_id) &&
      (!expectedId || v.responsibility_id === expectedId) &&
      (v.retention_state === "trashed" || v.retention_state === "purged") &&
      positive(v.retention_version) &&
      [
        "create",
        "pause",
        "resume",
        "cancel",
        "recheck",
        "acknowledge",
        "trash",
        "restore",
        "purge",
      ].includes(String(v.original_operation_kind)) &&
      (!expectedKind || v.original_operation_kind === expectedKind) &&
      (v.review_id === null || id(v.review_id)) &&
      v.recorded_success === true
    );
  }
  return (
    Object.keys(v).every((k) =>
      [
        "responsibility",
        "saved",
        "operation_id",
        "revision",
        "review_id",
        "acknowledged",
      ].includes(k),
    ) &&
    v.kind === undefined &&
    v.saved === true &&
    object(v.responsibility) &&
    id(v.responsibility.id) &&
    (!expectedId || v.responsibility.id === expectedId) &&
    positive(v.responsibility.version) &&
    v.responsibility.retention_state === "retained" &&
    positive(v.responsibility.retention_version) &&
    typeof v.responsibility.hidden === "boolean" &&
    typeof v.responsibility.status === "string" &&
    (v.acknowledged === undefined ||
      (v.acknowledged === true && id(v.review_id)))
  );
}
export function retentionBody(
  preview: RetentionPreview,
  permanentClick: boolean,
) {
  if (preview.action === "purge" && permanentClick !== true) return null;
  return {
    action: preview.action,
    expected_version: preview.responsibility.version,
    expected_retention_version: preview.responsibility.retention_version,
    preview_id: preview.preview_id,
    ...(preview.action === "purge"
      ? { confirm_permanent_removal: true as const }
      : {}),
  };
}
export function retentionDenial(error: unknown) {
  return (
    object(error) &&
    (error.status === 401 ||
      error.status === 403 ||
      /AUTH|SESSION|OWNER|PRIVATE|PRIVACY|CONTEXT_HIDDEN|CONTEXT_CHANGED/.test(
        String(error.code ?? ""),
      ))
  );
}
/** Only this open, authorized maintenance view holds recovery data. No storage or automatic retry. */
export class RetentionWriteQueue {
  private operation: {
    path: string;
    serialized: string;
    key: string;
    target: string;
    action: string;
  } | null = null;
  active = false;
  private transport: (path: string, options: RequestInit) => Promise<unknown>;
  private newId: () => string;
  constructor(
    transport: (path: string, options: RequestInit) => Promise<unknown>,
    newId: () => string,
  ) {
    this.transport = transport;
    this.newId = newId;
  }
  get pending() {
    return this.operation !== null;
  }
  clear() {
    this.operation = null;
  }
  async send(target: string, body: unknown) {
    if (this.active || this.operation) throw { code: "PRIVATE_WRITE_PENDING" };
    if (
      !object(body) ||
      !["trash", "restore", "purge"].includes(String(body.action))
    )
      throw { code: "RESPONSIBILITY_RETENTION_INVALID" };
    this.operation = {
      target,
      action: String(body.action),
      path: `/responsibilities/${encodeURIComponent(target)}/retention`,
      serialized: JSON.stringify(body),
      key: this.newId(),
    };
    return this.retry();
  }
  async retry(): Promise<WatchMutationResult> {
    if (!this.operation || this.active) throw { code: "PRIVATE_WRITE_BUSY" };
    const operation = this.operation;
    this.active = true;
    try {
      const result = await this.transport(operation.path, {
        method: "POST",
        body: operation.serialized,
        headers: { "X-Operation-Id": operation.key },
      });
      if (
        !validWatchMutationResult(
          result,
          operation.target,
          operation.key,
          operation.action,
        )
      )
        throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
      if (!("kind" in result) && !validMaintenanceRow(result.responsibility))
        throw { code: "RESPONSIBILITY_RESPONSE_INVALID" };
      if (this.operation === operation) this.operation = null;
      return result;
    } catch (error) {
      // Explicit rejections are safe to discard. Authority change clears the whole view elsewhere.
      // Unknown transport, malformed success and server failures keep the original exact request.
      if (
        object(error) &&
        integer(error.status) &&
        error.status >= 400 &&
        error.status < 500 &&
        error.status !== 408 &&
        !retentionDenial(error)
      )
        if (this.operation === operation) this.operation = null;
      throw error;
    } finally {
      this.active = false;
    }
  }
}
