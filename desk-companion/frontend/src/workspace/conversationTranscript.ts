import {
  needsOwnerReview,
  orderKey,
  orderStatus,
  type CommerceReview,
} from "./commercePresentation.ts";
import type { Translate } from "../types";
import type { InitiativeFinding } from "./InitiativeMessages";

export type ConversationTurn = {
  id: number | string;
  role: "user" | "assistant";
  body: string;
  at?: string;
  kind?: string;
  jobId?: string;
  orderKey?: string;
  orderVersion?: number;
  catchUpRef?: string;
  commerceChat?: string;
  googleRefreshEpoch?: number;
  approvalTask?: string | null;
  approvalSummary?: string;
  choices?: import("./commercePresentation").FlightAlternatives;
  voiceSession?: string;
  voiceGroup?: number;
  files?: Array<{ id: string; name: string }>;
};

type TimelineItem = { turn: ConversationTurn } | { finding: InitiativeFinding };
export function conversationWithFindings(turns: ConversationTurn[], findings: InitiativeFinding[]): TimelineItem[] {
  const byTime = [...findings].sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""));
  const rows: TimelineItem[] = [];
  let next = 0;
  for (const turn of turns) {
    const at = turn.at ? Date.parse(turn.at) : typeof turn.id === "number" ? turn.id : 0;
    while (next < byTime.length && Date.parse(byTime[next].created_at || "") < at) {
      rows.push({finding: byTime[next++]});
    }
    rows.push({turn});
  }
  return rows.concat(byTime.slice(next).map(finding => ({finding})));
}

/** Streaming Live text updates a speaker turn; playback never owns its history. */
export function appendLiveTranscript(
  previous: ConversationTurn[],
  session: string,
  fragment: { role?: string; text?: string; caption_group?: number; caption_replace?: boolean },
): ConversationTurn[] {
  const group = fragment.caption_group;
  if (!Number.isSafeInteger(group) || group! < 0 || !fragment.text)
    return previous;
  const role = fragment.role === "user" ? "user" : "assistant";
  const peers = previous.filter((turn) => turn.voiceSession === session);
  if (
    peers.length &&
    group! < Math.min(...peers.map((turn) => turn.voiceGroup!))
  )
    return previous;
  const id = `voice:${session}:${group}:${role}`;
  const existing = previous.findIndex((turn) => turn.id === id);
  if (existing >= 0)
    return previous.map((turn, index) =>
      index === existing
        ? { ...turn, body: (fragment.caption_replace && role === "assistant" ? fragment.text! : turn.body + fragment.text).slice(0, 8000) }
        : turn,
    );
  const turn: ConversationTurn = {
    id,
    at: new Date().toISOString(),
    role,
    body: fragment.text.slice(0, 8000),
    voiceSession: session,
    voiceGroup: group,
  };
  const index = previous.findIndex(
    (item) =>
      item.voiceSession === session &&
      (item.voiceGroup! > group! ||
        (item.voiceGroup === group &&
          role === "user" &&
          item.role === "assistant")),
  );
  const next = [...previous];
  next.splice(index < 0 ? next.length : index, 0, turn);
  return next.slice(-40);
}

export function latestAssistantReply(turns: ConversationTurn[]): string {
  const latest = turns.at(-1);
  return latest?.role === "assistant" ? latest.approvalSummary ?? latest.body : "";
}

export function asksApprovalStatus(text: string) {
  return /^(?:what needs my approval|(?:现在)?有什么需要我确认)\s*[？?。.!！]*$/i.test(text.trim());
}

/** Replace a just-shown pending result in place. Keep later user turns and never
 * repeat a transition received by both restoration and the foreground refresh. */
export function appendOrderUpdates(
  previous: ConversationTurn[],
  updates: CommerceReview[],
  chat: string,
  t: Translate,
): ConversationTurn[] {
  const next = [...previous];
  for (const row of updates) {
    const key = orderKey(row),
      id = `order/${key}/${row.version}`;
    if (next.some((turn) => turn.id === id)) continue;
    const turn: ConversationTurn = {
      id,
      role: "assistant",
      kind: "order_update",
      body: orderStatus(row, t),
      orderKey: key,
      orderVersion: row.version,
      commerceChat: chat,
    };
    if (next.at(-1)?.orderKey === key && next.at(-1)?.commerceChat === chat)
      next[next.length - 1] = turn;
    else next.push(turn);
  }
  return next.slice(-40);
}

/** A passive receipt can arrive while a person is about to accept a different
 * fare. Keep that review in place until the next deliberate conversation turn. */
export function focusedOrderTurn(
  turns: ConversationTurn[],
  rows: CommerceReview[],
) {
  const latest = turns.filter((turn) => turn.kind !== "quiet_catch_up").at(-1);
  if (latest?.kind !== "order_update") return latest;
  const pending = new Set(
    rows
      .filter(needsOwnerReview)
      .map(orderKey),
  );
  for (let i = turns.length - 1; i >= 0; i--) {
    const turn = turns[i];
    if (turn.kind === "quiet_catch_up") continue;
    if (turn.choices || (turn.orderKey && pending.has(turn.orderKey)))
      return turn;
    if (turn.kind !== "order_update") break;
  }
  return latest;
}

export function showOrderOnHome(row: CommerceReview, turn: ConversationTurn | undefined, allowPassive: boolean) {
  return (allowPassive && !row.quiet_update) ||
    (turn?.orderKey === orderKey(row) && turn.orderVersion === row.version);
}
