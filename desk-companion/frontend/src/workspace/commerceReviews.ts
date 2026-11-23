import { useCallback, useRef, useState } from "react";
import { request } from "../api";
import {
  orderKey,
  orderUpdates,
  watchedMarks,
  type CommerceReview,
  type StatusMark,
} from "./commercePresentation";
export {
  hkd,
  needsDecision,
  reviewRef,
  type CommerceReview,
  type CommerceRef,
} from "./commercePresentation";

const storageKey = "desk.flight-review-chat";
type Marker = { chat: string; task: string | null; watch?: StatusMark[] };
function loadMarker(): Marker | null {
  try {
    const marker = JSON.parse(sessionStorage.getItem(storageKey) ?? "null");
    if (
      !marker ||
      typeof marker.chat !== "string" ||
      (marker.task != null && typeof marker.task !== "string")
    )
      return null;
    return {
      ...marker,
      watch: Array.isArray(marker.watch)
        ? marker.watch.filter(
            (entry: StatusMark | null) =>
              entry &&
              ["shop", "flight"].includes(entry.kind) &&
              typeof entry.id === "string" &&
              typeof entry.state === "string" &&
              Number.isInteger(entry.version),
          )
        : [],
    };
  } catch {
    return null;
  }
}
function rowsFor(chat: string) {
  return request<{ rows: CommerceReview[]; has_flight_shortlist?: boolean }>(
    `/assistant/commerce-reviews?conversation_id=${encodeURIComponent(chat)}`,
  );
}
const settled = new Set([
  "cancelled",
  "completed",
  "expired",
  "failed",
  "unverified",
  "refunded",
  "refund_retry",
  "refund_review",
  "stopped",
  "manual",
]);

export function useCommerceReviews() {
  const [rows, setRows] = useState<CommerceReview[]>([]);
  const latest = useRef<CommerceReview[]>([]),
    tracked = useRef<string | undefined>(undefined),
    hasShortlist = useRef(false),
    refreshRequested = useRef(false),
    task = useRef<string | null>(null);
  const set = useCallback((items: CommerceReview[]) => {
    latest.current = items;
    setRows(items);
    if (tracked.current) {
      // The window remembers only versions of in-flight work. The server still
      // scopes every receipt read to the active login and original conversation.
      const marker = JSON.stringify({
        chat: tracked.current,
        task: task.current,
        watch: watchedMarks(items),
      });
      if (sessionStorage.getItem(storageKey) !== marker)
        sessionStorage.setItem(storageKey, marker);
    }
  }, []);
  const clear = useCallback(() => {
    tracked.current = undefined;
    hasShortlist.current = false;
    refreshRequested.current = false;
    task.current = null;
    sessionStorage.removeItem(storageKey);
    set([]);
  }, [set]);
  const receive = useCallback(
    (chat: string, row: CommerceReview | null, taskId?: string, shortlist = false) => {
      const others =
        tracked.current === chat
          ? latest.current.filter((item) => !row || orderKey(item) !== orderKey(row))
          : [];
      hasShortlist.current = shortlist || (tracked.current === chat && hasShortlist.current);
      refreshRequested.current = true;
      tracked.current = chat;
      task.current = taskId ?? null;
      set(row ? [row, ...others] : others);
    },
    [set],
  );
  const refresh = useCallback(
    async (chat: string | undefined) => {
      const previous = latest.current;
      if (
        !chat ||
        tracked.current !== chat ||
        (!refreshRequested.current && !previous.some((row) => !settled.has(row.state)))
      )
        return [];
      const result = await rowsFor(chat);
      if (tracked.current !== chat || latest.current !== previous) return [];
      refreshRequested.current = false;
      if (!result.rows.length && !result.has_flight_shortlist) {
        clear();
        return [];
      }
      hasShortlist.current = !!result.has_flight_shortlist;
      set(result.rows);
      return orderUpdates(watchedMarks(previous), result.rows);
    },
    [set, clear],
  );
  const restore = useCallback(
    async (taskId: string | undefined, current: () => boolean) => {
      const marker = loadMarker();
      if (!marker || marker.task !== (taskId ?? null)) return;
      const result = await rowsFor(marker.chat);
      if (!current() || loadMarker()?.chat !== marker.chat) return;
      if (!result.rows.length && !result.has_flight_shortlist) {
        clear();
        return;
      }
      tracked.current = marker.chat;
      hasShortlist.current = !!result.has_flight_shortlist;
      task.current = taskId ?? null;
      set(result.rows);
      return {
        chat: marker.chat,
        updates: orderUpdates(marker.watch ?? [], result.rows),
      };
    },
    [set, clear],
  );
  return { rows, tracked, hasShortlist, clear, receive, refresh, restore };
}
