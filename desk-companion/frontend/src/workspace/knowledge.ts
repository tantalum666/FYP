/** Owner-facing copy and actions for “what I know about you” and nudge history. */

export const knowledgeCopy = {
  title: ["What I know about you", "我了解的关于你的事"],
  nudgeTitle: ["Why did you nudge me", "为什么提醒我"],
  correct: ["Correct", "更正"],
  forget: ["Forget", "忘掉"],
  saveCorrection: ["Save correction", "保存更正"],
  expireWeek: ["Expire in 7 days", "7天后到期"],
  clearExpiry: ["Keep without expiry", "取消到期"],
  forgot: [
    "Memory deleted. It is removed from later requests and from replies saved on this desk. A live voice session ends. The provider's own logs are not erased.",
    "记忆已删除。之后的请求和本机保存的回复都不再包含它。正在进行的语音会话会结束。提供商自己保存的记录无法从这里清除。",
  ],
  emptyFacts: ["No saved facts yet.", "还没有保存的事实。"],
  emptyNudges: [
    "No morning briefing or evening check-in yet.",
    "还没有早晨简报或晚间检查。",
  ],
  dismiss: ["Dismiss", "知道了"],
  dismissed: ["Dismissed", "已关闭"],
} as const;

export type FactAction = "correct" | "forget" | "expire_week" | "clear_expiry";

export function actionsFor(
  section: "active" | "expired",
  expiresAt: string | null,
): FactAction[] {
  if (section === "expired") return ["forget"];
  return ["correct", "forget", expiresAt ? "clear_expiry" : "expire_week"];
}

export function sourceCopy(source: string): [string, string] {
  if (source === "owner") return ["Saved by you", "由你保存"];
  if (source === "conversation")
    return ["From a message you confirmed", "来自你确认的消息"];
  if (source === "assistant_confirmed")
    return ["From a draft you confirmed", "来自你确认的草稿"];
  return [source, source];
}

export function noteCopy(note: string): [string, string] | null {
  if (!note) return null;
  if (note === "explicit")
    return ["You asked to remember this.", "你要求记住这一点。"];
  if (note === "preference")
    return ["You stated a preference.", "你说了一项偏好。"];
  if (note === "identity") return ["You stated your name.", "你说了自己的名字。"];
  return [note, note];
}

export interface NudgeLine {
  id: string;
  reasonEn: string;
  reasonZh: string;
  summaryEn: string;
  summaryZh: string;
  canDismiss: boolean;
}

export function nudgeLine(nudge: {
  id: string;
  state: string;
  reason_en: string;
  reason_zh: string;
  summary_en: string;
  summary_zh: string;
}): NudgeLine {
  return {
    id: nudge.id,
    reasonEn: nudge.reason_en,
    reasonZh: nudge.reason_zh,
    summaryEn: nudge.summary_en,
    summaryZh: nudge.summary_zh,
    canDismiss: nudge.state === "open",
  };
}
