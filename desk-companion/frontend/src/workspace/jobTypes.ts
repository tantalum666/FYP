export type JobState =
  | "review"
  | "queued"
  | "running"
  | "verifying"
  | "succeeded"
  | "failed"
  | "cancel_requested"
  | "cancelled"
  | "expired"
  | "unknown";
export type JobAction =
  "save_note" | "verify_note" | "create_record" | "verify_record";
export type CreateJobAction = "save_note" | "create_record";
export interface ComputerJob {
  id: string;
  state: JobState;
  version: number;
  intent_hash?: string;
  expires_at: string;
  updated_at: string;
  error: string | null;
  cancel_requested: boolean;
  action: JobAction;
  task_id: string | null;
  request?: {
    title: string;
    content: string;
    artifact_id: string;
    task_version: number | null;
    target_origin?: string;
    app_instance_id?: string;
    adapter_version?: number;
    schema_version?: number;
    record_title?: string;
  };
  result: {
    verified: boolean;
    artifact?: string;
    bytes?: number;
    sha256?: string;
    reason?: string;
  } | null;
}
export function reviewAvailable(job: ComputerJob, now: number, fresh: boolean) {
  return fresh && !!job.request && !!job.intent_hash &&
    job.state === "review" && Date.parse(job.expires_at) > now;
}
export function jobCancellable(job: ComputerJob) {
  return (
    ["review", "queued", "running", "verifying", "unknown"].includes(
      job.state,
    ) && !job.cancel_requested
  );
}

export function recoveryMatchesNote(
  pending: { path: string; body: unknown } | null,
  title: string,
  content: string,
  taskId?: string,
  action: CreateJobAction = "save_note",
): boolean {
  if (
    !pending ||
    pending.path !== "/computer/jobs" ||
    !pending.body ||
    typeof pending.body !== "object"
  )
    return false;
  const body = pending.body as Record<string, unknown>;
  return (
    body.action === action &&
    body.title === title &&
    body.content === content &&
    (body.task_id ?? null) === (taskId ?? null)
  );
}

export function isApplicationJob(action: JobAction): boolean {
  return action === "create_record" || action === "verify_record";
}
export function verificationAction(
  action: JobAction,
): "verify_note" | "verify_record" {
  return isApplicationJob(action) ? "verify_record" : "verify_note";
}
