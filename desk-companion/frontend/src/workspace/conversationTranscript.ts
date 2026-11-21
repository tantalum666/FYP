import {
  orderKey,
  orderStatus,
  type CommerceReview,
} from "./commercePresentation.ts";
import type { Translate } from "../types";

export type ConversationTurn = {
  id: number | string;
  role: "user" | "assistant";
  body: string;
  kind?: string;
  jobId?: string;
  orderKey?: string;
  commerceChat?: string;
  choices?: import("./commercePresentation").FlightAlternatives;
  voiceSession?: string;
  voiceGroup?: number;
  files?: Array<{ id: string; name: string }>;
};

/** Streaming Live text updates a speaker turn; playback never owns its history. */
export function appendLiveTranscript(
  previous: ConversationTurn[],
  session: string,
  fragment: { role?: string; text?: string; caption_group?: number },
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
        ? { ...turn, body: (turn.body + fragment.text).slice(0, 8000) }
        : turn,
    );
  const turn: ConversationTurn = {
    id,
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
  return latest?.role === "assistant" ? latest.body : "";
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
      commerceChat: chat,
    };
    if (next.at(-1)?.orderKey === key && next.at(-1)?.commerceChat === chat)
      next[next.length - 1] = turn;
    else next.push(turn);
  }
  return next.slice(-40);
}
