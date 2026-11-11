/** Decisions for an owner-approved memory follow-up. The scheduler stays on the server. */

export type FollowUpState =
  | "pending"
  | "held"
  | "raised"
  | "handled"
  | "dismissed"
  | "cancelled";

export type FollowUpAction = "handled" | "snooze" | "dismissed";

export interface FollowUpView {
  id: string;
  memory_id: string;
  state: FollowUpState;
  version: number;
  due_local: string;
  timezone: string;
  body: string | null;
  memory_active: boolean;
  memory_updated: boolean;
  hold_reason: "quiet" | "proactivity" | null;
  reason_en: string;
  reason_zh: string;
  armed: boolean;
}

export interface FollowUpDraft {
  memory_id: string;
  memory_version: number;
  body: string;
  due_local: string;
  timezone: string;
  armed: false;
}

const OPEN = new Set(["pending", "held", "raised"]);

export function followUpActions(state: string): FollowUpAction[] {
  if (state === "raised") return ["handled", "snooze", "dismissed"];
  if (state === "pending" || state === "held") return ["dismissed"];
  return [];
}

export function memoriesWithoutOpenFollowUp<T extends { id: string }>(
  facts: T[],
  followups: Array<{ memory_id: string; state: string }>,
): T[] {
  const open = new Set(
    followups.filter((item) => OPEN.has(item.state)).map((item) => item.memory_id),
  );
  return facts.filter((fact) => !open.has(fact.id));
}

export function draftIsUnarmed(draft: { armed: boolean; saved: boolean }): boolean {
  return draft.armed === false && draft.saved === false;
}

export function followUpErrorCopy(code: string): [string, string] | null {
  const messages: Record<string, [string, string]> = {
    FOLLOWUP_TIME_PAST: [
      "Choose a time that has not arrived yet.",
      "请选择一个还没到的时间。",
    ],
    FOLLOWUP_TIME_INVALID: [
      "That local time is missing or happens twice. Choose another time.",
      "这个本地时间不存在或出现了两次。请另选时间。",
    ],
    FOLLOWUP_TIME_REQUIRED: [
      "A follow-up needs a time. Leaving it blank does not clear the saved time.",
      "跟进需要一个时间。留空不会清掉已保存的时间。",
    ],
    MEMORY_FOLLOWUP_OPEN: [
      "This memory already has a follow-up. Dismiss that one before adding another.",
      "这条记忆已经有一次跟进。请先关闭它，再添加下一次。",
    ],
    MEMORY_FOLLOWUP_LIMIT: [
      "Too many follow-ups are still open.",
      "未完成的跟进太多了。",
    ],
    FOLLOWUP_NOT_RAISED: [
      "Remind me in an hour is available after Alice raises it.",
      "要等 Alice 提醒之后，才能再推迟一小时。",
    ],
    FOLLOWUP_CLOSED: [
      "This follow-up is already closed.",
      "这次跟进已经结束。",
    ],
  };
  return messages[code] ?? null;
}
