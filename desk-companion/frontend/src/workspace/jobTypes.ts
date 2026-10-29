import type { Translate } from "../types";

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
  title?: string;
  authorization?: { mode: "once" | "full"; version?: number } | null;
  id: string;
  state: JobState;
  version: number;
  intent_hash: string;
  expires_at: string;
  updated_at: string;
  error: string | null;
  cancel_requested: boolean;
  action:
    | "save_note"
    | "verify_note"
    | "save_folder_file"
    | "verify_folder_file"
    | "linux_note_preview"
    | "verify_linux_file";
  task_id: string | null;
  request: {
    title: string;
    content: string;
    artifact_id: string;
    task_version: number | null;
    folder_label?: string;
    folder_fingerprint?: string;
  };
  result: {
    verified: boolean;
    artifact?: string;
    bytes?: number;
    sha256?: string;
    reason?: string;
    apps_verified?: string[];
  } | null;
}
export function isFolderAction(action: ComputerJob["action"]) {
  return action === "save_folder_file" || action === "verify_folder_file";
}

export function isDesktopAction(action: ComputerJob["action"]) {
  return action === "linux_note_preview" || action === "verify_linux_file";
}

export function reviewAvailable(job: ComputerJob, now: number, fresh: boolean) {
  return fresh && job.state === "review" && Date.parse(job.expires_at) > now;
}
const READ_BACK: Record<string, [string, string]> = {
  workflow_incomplete: [
    "The file may exist, but both application steps were not verified. Review the desktop before preparing another job.",
    "文件可能已保存，但两个应用步骤尚未全部核验。请先检查桌面，再决定是否准备另一项作业。",
  ],
  content_mismatch: [
    "The file does not match the approved text. It was left unchanged.",
    "文件与批准全文不一致，原文件没有被修改。",
  ],
  artifact_missing: [
    "No file was found at the approved name. Nothing was created to fill the gap.",
    "批准的文件名下没有文件，系统没有另建一个来补上。",
  ],
  target_denied: [
    "The file could not be read safely. Check the folder, then run the check again.",
    "无法安全读取该文件。请检查文件夹后再核验。",
  ],
  verification_unavailable: [
    "Read-back is unavailable. Run the check again once the folder can be read.",
    "暂时无法读回。文件夹可读之后再核验。",
  ],
};

export function readBackCopy(
  reason: string | undefined,
): [string, string] | null {
  if (!reason || reason === "read_back_matches") return null;
  return READ_BACK[reason] ?? null;
}

export function recoveryCopy(job: ComputerJob): [string, string] | null {
  const reason = job.result?.reason;
  if (reason === "content_mismatch" || reason === "artifact_missing") {
    return [
      "Next step: check the file named above. Prepare a new job only if you want a different file.",
      "下一步：核验上面的文件名。只有需要另一份文件时才重新准备作业。",
    ];
  }
  if (job.error === "PERMISSION_CHANGED")
    return [
      "Your automatic permission changed before this action started. Ask Alice to prepare it again.",
      "操作开始前自动权限已改变，请让 Alice 重新准备。",
    ];
  if (job.error === "COMPUTER_SCOPE_CHANGED") {
    return [
      "Next step: prepare a new job for the current folder. This card stays as the record.",
      "下一步：按当前文件夹重新准备作业。这张卡片仍保留为记录。",
    ];
  }
  if (job.state === "cancelled") {
    return [
      "No new file was written for this job.",
      "这次作业没有写入新文件。",
    ];
  }
  return null;
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
  action: ComputerJob["action"] = "save_note",
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

/** Safe task-detail projection; full text/intent are owner-review only. */
export type ComputerJobSummary = Omit<ComputerJob, "request" | "intent_hash">;

export function jobStateLabel(state: JobState, t: Translate): string {
  return {
    review: t("Needs your approval", "待你批准"),
    queued: t("Queued", "已排队"),
    running: t("Saving or checking", "正在保存或检查"),
    verifying: t("Verifying result", "正在核验结果"),
    succeeded: t("Verified", "已核验"),
    failed: t("Could not execute", "未能执行"),
    cancel_requested: t("Stopping · result pending", "正在停止 · 结果待确认"),
    cancelled: t("Cancelled before execution", "已在执行前取消"),
    expired: t("Expired without execution", "已到期，未执行"),
    unknown: t("Result unknown · check before retrying", "结果未知 · 请先核验"),
  }[state];
}
