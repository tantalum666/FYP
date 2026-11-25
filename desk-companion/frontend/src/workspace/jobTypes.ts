import type { Translate } from "../types";
import type { ApplicationStep } from "./applicationTypes";
import type { Quote, QuoteRequest } from "./CommerceQuote";

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
  | "unknown"
  | "owner_takeover";
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
    | "verify_linux_file"
    | "application"
    | "computer_use";
  task_id: string | null;
  request: {
    title: string;
    content: string;
    artifact_id: string;
    task_version: number | null;
    folder_label?: string;
    folder_fingerprint?: string;
    stage?: string;
    step?: ApplicationStep;
    start_url?: string;
    engine?: "local" | "managed";
    max_steps?: number;
    allowed_origins?: string[];
    quote_request?: QuoteRequest;
  };
  result: {
    verified: boolean;
    artifact?: string;
    bytes?: number;
    sha256?: string;
    reason?: string;
    apps_verified?: string[];
    outcome?: "review_ready" | "needs_owner" | "step_limit";
    quality?: string;
    readback?: {
      quote?: Quote;
      reason?: string;
      report?: string;
      resumable?: boolean;
      data_scope?: string;
    };
    owner_input?: { nonce: string; origin: string; phase: string };
    paused?: boolean;
    takeover_available?: boolean;
    sample_input?: boolean;
    phase?: "paused" | "held" | "returning";
    wall?: "login" | "otp" | "captcha" | "payment";
    needed?: string;
  } | null;
}

const OWNER_WALL: Record<string, [string, string]> = {
  login: [
    "Sign in on this page. Alice will not type your password.",
    "请在这一页登录。Alice 不会输入密码。",
  ],
  otp: [
    "Enter the SMS code on this page. Alice will not type or store it.",
    "请在这一页输入短信验证码。Alice 不会输入或保存验证码。",
  ],
  captcha: [
    "Complete the site check on this page. Alice will not solve it.",
    "请在这一页完成网站验证。Alice 不会代为通过。",
  ],
  payment: [
    "Confirm payment on this page. Alice will not submit it or enter a card.",
    "请在这一页确认付款。Alice 不会提交，也不会输入银行卡。",
  ],
};

export function ownerWallCopy(
  wall: string | undefined,
): [string, string] | null {
  if (!wall) return null;
  return OWNER_WALL[wall] ?? null;
}
export function isApplicationAction(action: ComputerJob["action"]) {
  return action === "application";
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
  if (job.error === "BROWSER_PAGE_LOST")
    return [
      "The page closed. Alice did not open another one. Check the result before trying again.",
      "页面已关闭。Alice 没有再打开新的页面。请先核验结果再重试。",
    ];
  if (job.error === "COMPUTER_SCOPE_CHANGED") {
    return [
      "Next step: prepare a new job for the current folder. This card stays as the record.",
      "下一步：按当前文件夹重新准备作业。这张卡片仍保留为记录。",
    ];
  }
  if (job.state === "cancelled") {
    if (job.action === "computer_use")
      return [
        "Browser stopped; earlier steps may remain.",
        "浏览器已停止，之前的步骤可能已经生效。",
      ];
    if (isApplicationAction(job.action))
      return [
        "Stopped before publishing this file revision.",
        "已在发布本次文件修订前停止。",
      ];
    if (
      job.error === "USER_CANCELLED" ||
      job.error === "JOB_CANCELLED_BEFORE_DISPATCH"
    )
      return [
        "No new file was written for this job.",
        "这次作业没有写入新文件。",
      ];
    return [
      "Cancelled. The outcome was not checked. Check result only rereads the file.",
      "已取消。结果尚未核验。核验只会重新读取文件。",
    ];
  }
  return null;
}

export function jobCancellable(job: ComputerJob) {
  return (
    [
      "review",
      "queued",
      "running",
      "verifying",
      "unknown",
      "owner_takeover",
    ].includes(job.state) && !job.cancel_requested
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

/** What a returning owner can safely do with one linked file action. */
export function taskRecoveryGuidance(job: {
  state: string;
  action?: string;
  error?: string | null;
  result?: { verified?: boolean } | null;
}): {
  kind: "unknown" | "needs_approval" | "checked" | "nothing_written" | "stopped" | "unconfirmed";
  text: [string, string];
} | null {
  if (job.state === "unknown")
    return {
      kind: "unknown",
      text: [
        "The saved result is unknown. The safe next step is Check result on this file in the chat. That only rereads the file.",
        "已保存的结果未知。安全的下一步是在对话中核验这个文件。核验只会重新读取文件。",
      ],
    };
  if (job.state === "review")
    return {
      kind: "needs_approval",
      text: [
        "This action is waiting for your approval. Opening the chat does not approve or send it.",
        "这个操作正在等待你的批准。打开对话不会批准或发送它。",
      ],
    };
  if (job.state === "succeeded" && job.result?.verified)
    return {
      kind: "checked",
      text: [
        "Result checked. The file was not written again.",
        "结果已核验。文件没有被再次写入。",
      ],
    };
  if (job.state === "cancelled" && job.action === "computer_use")
    return {
      kind: "stopped",
      text: [
        "Browser stopped; earlier steps may remain. Opening the chat does not continue that browser.",
        "浏览器已停止，之前的步骤可能已经生效。打开对话不会继续那个浏览器。",
      ],
    };
  // Cancel from review/queue, or a checkpoint rejection before the write.
  // Failure, expiry, and any other cancellation can follow a dispatched effect.
  if (
    job.state === "cancelled" &&
    job.action !== "computer_use" &&
    (job.error === "USER_CANCELLED" || job.error === "JOB_CANCELLED_BEFORE_DISPATCH")
  )
    return {
      kind: "nothing_written",
      text: [
        "No new file was written for this action.",
        "这次操作没有写入新文件。",
      ],
    };
  if (job.state === "cancelled" || job.state === "failed" || job.state === "expired")
    return {
      kind: "unconfirmed",
      text: [
        "This action stopped without a checked result. Check the existing file before another write. That check only rereads.",
        "这个操作已停止，结果尚未核验。再次写入前请先核验已有文件。核验只会重新读取。",
      ],
    };
  return null;
}

export function jobStateLabel(state: JobState, t: Translate): string {
  return {
    review: t("Needs your approval", "待你批准"),
    queued: t("Queued", "已排队"),
    running: t("Saving or checking", "正在保存或检查"),
    verifying: t("Verifying result", "正在核验结果"),
    succeeded: t("Verified", "已核验"),
    failed: t("Could not execute", "未能执行"),
    cancel_requested: t("Stopping · result pending", "正在停止 · 结果待确认"),
    cancelled: t("Cancelled", "已取消"),
    expired: t("Expired without execution", "已到期，未执行"),
    unknown: t("Result unknown · check before retrying", "结果未知 · 请先核验"),
    owner_takeover: t("Waiting for you", "等待你接手"),
  }[state];
}
