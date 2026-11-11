import type { Translate } from "../types";

export function isJourneyAdvice(kind: string | undefined): boolean {
  return (
    kind === "mailbox_reply" ||
    kind === "shopping_advice" ||
    kind === "calendar_advice"
  );
}

export function proposalDecisionNotice(
  result: { queued?: boolean; kind?: string },
  action: "confirm" | "cancel",
  requestedKind: string | undefined,
  t: Translate,
): string {
  if (result.queued)
    return t(
      "Action queued. Check the device receipt for its result.",
      "动作已排队，请在设备回执中查看结果。",
    );
  if (action === "cancel") return t("Draft cancelled.", "草稿已取消。");
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
