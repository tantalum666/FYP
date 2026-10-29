import { request, write } from "../api";
import type { ComputerJob } from "./jobTypes";
import { isDesktopAction, isFolderAction } from "./jobTypes";
import type { Task } from "./taskTypes";

export type JobAction = "approve" | "cancel" | "reconcile" | "verify";

/** One request contract for conversation cards and the secondary activity view. */
export async function requestJobAction(job: ComputerJob, action: JobAction) {
  if (action === "approve") {
    return write(`/computer/jobs/${job.id}/approve`, {
      expected_version: job.version,
      intent_hash: job.intent_hash,
    });
  }
  if (action === "verify") {
    const task = job.task_id
      ? (await request<{ task: Task }>(`/tasks/${job.task_id}`)).task
      : null;
    return write("/computer/jobs", {
      action: isDesktopAction(job.action)
        ? "verify_linux_file"
        : isFolderAction(job.action)
          ? "verify_folder_file"
          : "verify_note",
      title: job.request.title,
      source_job_id: job.id,
      task_id: job.task_id,
      task_version: task?.version ?? null,
    });
  }
  // Cancellation and read-only reconciliation remain available outside the normal write queue.
  return request(`/computer/jobs/${job.id}/${action}`, {
    method: "POST",
    body: "{}",
    headers: { "X-Operation-Id": `computer-${action}/${job.id}` },
  });
}
