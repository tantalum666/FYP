import type { WatchMaintenanceUsage } from "./retention";
export const watchedFields = [
  "status",
  "due",
  "next_step",
  "waiting_for",
  "steps",
  "progress",
] as const;
export type WatchedField = (typeof watchedFields)[number];
export type WatchAction = "pause" | "resume" | "cancel" | "recheck";
export interface Responsibility {
  id: string;
  version: number;
  generation: number;
  retention_state?: "retained" | "trashed";
  retention_version?: number;
  trashed_at?: string | null;
  restored_at?: string | null;
  purged_at?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  baseline_at: string;
  expires_at: string;
  review_budget: number;
  reviews_used: number;
  daily_review_budget: number;
  budget_day: string;
  daily_used: number;
  blocked_code: string | null;
  pending_count: number;
  hidden: boolean;
  title?: string;
  kind?: "selected_task_changes";
  task_ids?: string[];
  fields?: WatchedField[];
  retain_change_history?: true;
}
export interface WatchReview {
  id: string;
  responsibility_id: string;
  sequence: number;
  version: number;
  delivery_state: "pending" | "acknowledged" | "dismissed";
  changed_ids: string[];
  changed_fields: WatchedField[];
  first_observed_at: string;
  last_observed_at: string;
  catch_up: boolean;
  result_code: "SELECTED_TASK_FIELDS_CHANGED";
  title_source: "current_record";
}
export interface WatchDetail {
  responsibility: Responsibility;
  reviews: WatchReview[];
  selected_tasks: {
    id: string;
    title: string;
    available: boolean;
    version: number | null;
  }[];
  revision: number;
}
export interface WatchList {
  maintenance_usage?: WatchMaintenanceUsage;
  responsibilities: Responsibility[];
  pending_count: number;
  hidden: boolean;
  revision: number;
  server_time: string;
  limits: Record<string, number>;
}
export interface WatchScope {
  tasks: { id: string; title: string; version: number; status: string }[];
  selected_task_ids: string[];
  fields: WatchedField[];
  scope_revision: string | null;
  server_time: string;
  limits: Record<string, number>;
  truncated: boolean;
}
export interface WatchDraft {
  title: string;
  task_ids: string[];
  fields: WatchedField[];
  expires_at: string;
  review_budget: number;
  daily_review_budget: number;
  retain_change_history: boolean;
}
export function newWatchDraft(): WatchDraft {
  return {
    title: "",
    task_ids: [],
    fields: ["status", "due", "progress"],
    expires_at: "",
    review_budget: 20,
    daily_review_budget: 10,
    retain_change_history: false,
  };
}
export function exactIds(a: string[], b: string[]) {
  return (
    a.length === b.length &&
    new Set(a).size === a.length &&
    a.every((id) => b.includes(id))
  );
}
export function scopePath(ids: string[], fields: WatchedField[]) {
  const params = new URLSearchParams();
  ids.forEach((id) => params.append("task_id", id));
  fields.forEach((field) => params.append("field", field));
  return `/responsibilities/scope?${params}`;
}
export function prepareWatch(
  draft: WatchDraft,
  scope: WatchScope | null,
  now = Date.now(),
) {
  const expires = Date.parse(
    draft.expires_at.endsWith("Z") ? draft.expires_at : draft.expires_at + "Z",
  );
  if (
    !scope?.scope_revision ||
    !/^[a-f0-9]{64}$/.test(scope.scope_revision) ||
    !draft.title.trim() ||
    Array.from(draft.title.trim()).length > 160 ||
    !draft.retain_change_history ||
    !draft.task_ids.length ||
    draft.task_ids.length > 10 ||
    !exactIds(draft.task_ids, scope.selected_task_ids) ||
    !exactIds(draft.fields, scope.fields) ||
    !draft.fields.length ||
    draft.fields.some((field) => !watchedFields.includes(field)) ||
    !draft.task_ids.every((id) => scope.tasks.some((task) => task.id === id)) ||
    !Number.isFinite(expires) ||
    expires <= now ||
    expires > now + 30 * 86400000 ||
    !Number.isInteger(draft.review_budget) ||
    draft.review_budget < 1 ||
    draft.review_budget > 100 ||
    !Number.isInteger(draft.daily_review_budget) ||
    draft.daily_review_budget < 1 ||
    draft.daily_review_budget > 20
  )
    return null;
  return {
    title: draft.title.trim(),
    kind: "selected_task_changes" as const,
    task_ids: [...draft.task_ids],
    fields: [...draft.fields],
    scope_revision: scope.scope_revision,
    retain_change_history: true as const,
    expires_at: new Date(expires).toISOString(),
    review_budget: draft.review_budget,
    daily_review_budget: draft.daily_review_budget,
  };
}
export function watchActions(status: string, hidden = false): WatchAction[] {
  if (status === "active") return ["pause", "cancel"];
  if (status === "paused") return hidden ? ["cancel"] : ["resume", "cancel"];
  if (status === "blocked")
    return hidden ? ["pause", "cancel"] : ["recheck", "pause", "cancel"];
  return [];
}
/** Discard unexpected private fields before a hidden response enters React state. */
export function metadataOnly(row: Responsibility): Responsibility {
  return {
    id: row.id,
    version: row.version,
    generation: row.generation,
    status: row.status,
    created_at: row.created_at,
    updated_at: row.updated_at,
    baseline_at: row.baseline_at,
    expires_at: row.expires_at,
    review_budget: row.review_budget,
    reviews_used: row.reviews_used,
    daily_review_budget: row.daily_review_budget,
    budget_day: row.budget_day,
    daily_used: row.daily_used,
    blocked_code: null,
    pending_count: row.pending_count,
    hidden: true,
  };
}
export function followupTaskIds(detail: WatchDetail): string[] | null {
  const ids = detail.responsibility.task_ids;
  if (
    !ids?.length ||
    ids.length > 10 ||
    new Set(ids).size !== ids.length ||
    !ids.every((id) =>
      detail.selected_tasks.some((task) => task.id === id && task.available),
    )
  )
    return null;
  return [...ids];
}
