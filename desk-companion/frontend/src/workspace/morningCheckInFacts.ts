/** Decisions for one morning check-in. The scheduler stays on the server. */

export interface MorningCitation {
  followup_id: string;
  memory_id: string;
  body: string;
}

export interface MorningDraft {
  due_local: string;
  timezone: string;
  citations: MorningCitation[];
  ready: boolean;
  armed: false;
}

export interface MorningCheckInView {
  id: string;
  state: "pending" | "held" | "raised" | "dismissed";
  version: number;
  due_local: string;
  timezone: string;
  citations: MorningCitation[];
  left_out: number;
  armed: boolean;
  reason_en: string;
  reason_zh: string;
}

export function checkInReady(citationCount: number): boolean {
  return citationCount >= 2;
}

export function visibleCitations(citations: Array<{ body: string | null }>): string[] {
  return citations.flatMap((item) => {
    const body = item.body?.trim();
    return body ? [body] : [];
  });
}

export function morningErrorCopy(code: string): [string, string] | null {
  const messages: Record<string, [string, string]> = {
    MORNING_CHECKIN_NEEDS_SEVERAL: [
      "Choose a time that covers at least two follow-ups.",
      "请选择一个能覆盖至少两条跟进的时间。",
    ],
    MORNING_CHECKIN_OPEN: [
      "A morning check-in is already scheduled. Dismiss it before approving another.",
      "已经有一次早晨核对。请先关闭它，再批准下一次。",
    ],
    MORNING_CHECKIN_CLOSED: [
      "This morning check-in is already closed.",
      "这次早晨核对已经结束。",
    ],
  };
  return messages[code] ?? null;
}
