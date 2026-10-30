import { errorText } from "../../api";
import type { Translate } from "../../types";
import type { WatchedField, WatchAction } from "./types";
export function fieldLabel(field: WatchedField, t: Translate) {
  return {
    status: t("Status", "状态"),
    due: t("Due date and timezone", "截止日期与时区"),
    next_step: t("Next step", "下一步"),
    waiting_for: t("Waiting for", "等待事项"),
    steps: t("Checklist steps", "步骤清单"),
    progress: t("New progress notes", "新增进展记录"),
  }[field];
}
export function actionLabel(action: WatchAction, t: Translate) {
  return {
    pause: t("Pause", "暂停"),
    resume: t("Resume from now", "从现在恢复"),
    cancel: t("Cancel watch", "取消关注"),
    recheck: t("Recheck sources", "重新检查来源"),
  }[action];
}
export function statusLabel(status: string, t: Translate) {
  return (
    {
      active: t("Active", "关注中"),
      paused: t("Paused", "已暂停"),
      cancelled: t("Cancelled", "已取消"),
      expired: t("Expired", "已到期"),
      budget_exhausted: t("Lifetime limit reached", "已达总次数上限"),
      blocked: t("Source check blocked", "来源检查受阻"),
      pending: t("Pending review", "待查看"),
      acknowledged: t("Acknowledged", "已查看"),
      dismissed: t("Dismissed", "已撤销"),
    }[status] ?? t("Unknown status", "未知状态")
  );
}
export function watchError(error: unknown, t: Translate) {
  const code =
    error && typeof error === "object" && "code" in error
      ? String(error.code)
      : "";
  const messages: Record<string, string> = {
    RESPONSIBILITY_REMOVED: t(
      "This exact watch history was permanently removed. Opaque retry metadata remains; it cannot be restored.",
      "此确切关注历史已永久移除。不含正文的重试元数据仍保留，无法恢复。",
    ),
    RESPONSIBILITY_RETENTION_INVALID: t(
      "This history is no longer in the required state. Refresh its current disposition; no replacement action was started.",
      "此历史已不处于所需状态，请刷新当前留存状态；未开始替代操作。",
    ),
    RESPONSIBILITY_RETAINED_STATE_REQUIRED: t(
      "This watch is in Trash or permanently removed. Open history maintenance to inspect its current state.",
      "此关注在废纸篓或已永久移除，请打开历史整理查看当前状态。",
    ),
    RESPONSIBILITY_PREVIEW_EXPIRED: t(
      "The preview expired or is no longer available. A new action requires a new preview; recover an unknown sent request only with its original retry.",
      "预览已到期或不可用。新操作需重新预览；已发送但未知的请求只能按原始请求重试。",
    ),
    RESPONSIBILITY_PREVIEW_CHANGED: t(
      "The exact history or authority changed. Refresh and review a new action-specific preview.",
      "确切历史或权限已变化，请刷新并重新审阅此操作的预览。",
    ),
    RESPONSIBILITY_METADATA_LIMIT: t(
      "All 256 lifetime watch identities are used. Removing history does not reset this limit. Existing recovery and final stop controls remain available.",
      "256个生命周期关注标识均已使用，移除历史不会重置此上限。仍可恢复原操作回执及使用最终停止控制。",
    ),
    RESPONSIBILITY_METADATA_UNAVAILABLE: t(
      "Retained metadata cannot be counted safely. Usage is unknown; do not assume free space. Existing records were not discarded.",
      "无法安全计量留存元数据，用量未知，请勿假定有空余容量。现有记录未被丢弃。",
    ),
    RESPONSIBILITY_NOT_TERMINAL: t(
      "Cancel this watch first using its existing controls. History maintenance never cancels it automatically.",
      "请先使用原有控制取消此关注，历史整理不会自动取消。",
    ),
    RESPONSIBILITY_CONTEXT_CHANGED: t(
      "Private context changed before the response arrived. The action may already have saved; reopen current history before repeating it.",
      "响应返回前私人上下文已变化。操作可能已保存；重复操作前请重新打开当前历史。",
    ),
    RESPONSIBILITY_SCOPE_CHANGED: t(
      "Selected records changed. Refresh and review the exact selection again.",
      "所选记录已变化，请刷新并重新审阅确切选择。",
    ),
    RESPONSIBILITY_SOURCE_UNAVAILABLE: t(
      "An enrolled task is unavailable. No replacement or smaller selection was used.",
      "已关注的事务不可用，未替换来源或缩小选择。",
    ),
    RESPONSIBILITY_SOURCE_KIND_UNSUPPORTED: t(
      "Only selected local tasks can be watched here.",
      "此处仅支持关注明确选择的本地事务。",
    ),
    RESPONSIBILITY_NOT_FOUND: t(
      "This watch is unavailable. Refresh the list.",
      "此关注不可用，请刷新列表。",
    ),
    RESPONSIBILITY_CLOSED: t(
      "This watch has ended. Starting again requires a new reviewed enrollment.",
      "此关注已结束，重新开始需新建并审阅。",
    ),
    RESPONSIBILITY_LIMIT: t(
      "The watch limit was reached. No new watch was created.",
      "已达到关注上限，未创建新的关注。",
    ),
    RESPONSIBILITY_ACTION_INVALID: t(
      "This control is no longer available. Refresh its status.",
      "此操作已不可用，请刷新状态。",
    ),
    RESPONSIBILITY_EXPIRY_INVALID: t(
      "Choose a future UTC expiry within 30 days.",
      "请选择未来30天内的UTC到期时间。",
    ),
    RESPONSIBILITY_OPERATION_LIMIT: t(
      "The control history limit was reached. Final stop controls remain available.",
      "已达到操作记录上限，仍可使用最终停止操作。",
    ),
    REVIEW_NOT_FOUND: t(
      "This review is no longer available. Refresh the history.",
      "此审阅已不可用，请刷新历史。",
    ),
    REVIEW_CHANGED: t(
      "New changes joined this review. Read the refreshed version before acknowledging.",
      "新的变化已合并至此审阅，请查看刷新后的版本再确认已查看。",
    ),
    REVIEW_NOT_PENDING: t(
      "This review is no longer pending. Refresh its status.",
      "此审阅已不再待查看，请刷新状态。",
    ),
    VERSION_CONFLICT: t(
      "This watch changed. Refresh before choosing the control again.",
      "此关注已变化，请刷新后重新选择操作。",
    ),
    RESPONSIBILITY_RESPONSE_INVALID: t(
      "The response could not be validated. Refresh before continuing.",
      "无法核验响应，请刷新后继续。",
    ),
  };
  return messages[code] ?? errorText(error, t);
}
