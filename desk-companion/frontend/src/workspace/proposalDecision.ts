import type { Translate } from "../types";

export function isJourneyAdvice(kind: string | undefined): boolean {
  return (
    kind === "mailbox_reply" ||
    kind === "shopping_advice" ||
    kind === "calendar_advice"
  );
}

export function proposalDecisionNotice(
  result: { queued?: boolean; kind?: string; paused?: boolean },
  action: "confirm" | "cancel",
  requestedKind: string | undefined,
  t: Translate,
): string {
  if (action === "cancel") return t("Draft cancelled.", "草稿已取消。");
  if ((result.kind ?? requestedKind) === "mail_followup")
    return result.paused
      ? t(
          "Email follow-up saved. Checks are paused in your preferences.",
          "邮件跟进已保存，当前已按偏好暂停检查。",
        )
      : t(
          "Email follow-up saved. New replies will appear in the linked task.",
          "邮件跟进已保存，新回复会显示在关联事务中。",
        );
  if ((result.kind ?? requestedKind) === "browser_research")
    return result.queued
      ? t(
          "Browser task started. Its progress stays in this conversation.",
          "浏览器任务已开始，进度会留在这段对话里。",
        )
      : t("Browser task status refreshed.", "已更新浏览器任务的状态。");
  if (result.queued)
    return t(
      "Action queued. Check the device receipt for its result.",
      "动作已排队，请在设备回执中查看结果。",
    );
  const kind = result.kind ?? requestedKind;
  if (kind === "email_send")
    return t("Email accepted for sending.", "邮件已提交发送。");
  if (isJourneyAdvice(kind))
    return t("Review saved to the task.", "核对记录已保存到事务。");
  if (kind?.startsWith("task_"))
    return t(
      "Task saved. Its progress is kept between conversations.",
      "事务已保存，进展会在交谈之间保留。",
    );
  if (kind?.startsWith("memory_")) return t("Memory updated.", "记忆已更新。");
  if (kind === "create" || kind === "change")
    return t("Saved to your calendar.", "已保存到日历。");
  return t("Update saved.", "更新已保存。");
}
