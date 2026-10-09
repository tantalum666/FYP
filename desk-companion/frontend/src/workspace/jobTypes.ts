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
export interface ComputerJob {
  id: string;
  state: JobState;
  version: number;
  intent_hash: string;
  expires_at: string;
  updated_at: string;
  error: string | null;
  cancel_requested: boolean;
  action: "save_note" | "verify_note";
  task_id: string | null;
  request: {
    title: string;
    content: string;
    artifact_id: string;
    task_version: number | null;
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
  return fresh && job.state === "review" && Date.parse(job.expires_at) > now;
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
    body.action === "save_note" &&
    body.title === title &&
    body.content === content &&
    (body.task_id ?? null) === (taskId ?? null)
  );
}
