import { useCallback, useRef, useState } from "react";
import { request } from "../api";
import type { SandboxFlight } from "./SandboxFlightBooking";
import type { SandboxShop } from "./SandboxShopOrder";

export type CommerceReview =
  (SandboxFlight & { kind: "flight" }) | (SandboxShop & { kind: "shop" });
export type CommerceRef = {
  id: string;
  version: number;
  amount_minor: number;
  kind: "flight" | "shop";
};
export const reviewRef = (
  row: Pick<CommerceReview, "id" | "version" | "review_minor">,
  kind: CommerceRef["kind"],
): CommerceRef => ({
  id: row.id,
  version: row.version,
  amount_minor: row.review_minor,
  kind,
});
export const needsDecision = (row: { state: string }) =>
  ["quoted", "reprice", "submit_unknown", "retry"].includes(row.state);
export const hkd = (minor: number) => `HK$${(minor / 100).toFixed(2)}`;

export function useCommerceReviews() {
  const [rows, setRows] = useState<CommerceReview[]>([]);
  const tracked = useRef<string | undefined>(undefined);
  const latest = useRef<CommerceReview[]>([]);
  const set = useCallback((items: CommerceReview[]) => {
    latest.current = items;
    setRows(items);
  }, []);
  const clear = useCallback(() => {
    tracked.current = undefined;
    sessionStorage.removeItem("desk.flight-review-chat");
    set([]);
  }, [set]);
  const receive = useCallback(
    (chat: string, row: CommerceReview, task?: string) => {
      sessionStorage.setItem(
        "desk.flight-review-chat",
        JSON.stringify({ chat, task: task ?? null }),
      );
      const other =
        tracked.current === chat
          ? latest.current.filter((x) => x.id !== row.id || x.kind !== row.kind)
          : [];
      tracked.current = chat;
      set([row, ...other]);
    },
    [set],
  );
  const refresh = useCallback(
    async (chat: string | undefined) => {
      if (
        !chat ||
        tracked.current !== chat ||
        !latest.current.some(
          (row) =>
            ![
              "cancelled",
              "completed",
              "expired",
              "failed",
              "unverified",
            ].includes(row.state),
        )
      )
        return;
      const previous = latest.current;
      const response = await request<{ rows: CommerceReview[] }>(
        `/assistant/commerce-reviews?conversation_id=${encodeURIComponent(chat)}`,
      );
      if (tracked.current === chat && previous === latest.current)
        set(response.rows);
    },
    [set],
  );
  const restore = useCallback(
    async (task: string | undefined, stillCurrent: () => boolean) => {
      const raw = sessionStorage.getItem("desk.flight-review-chat");
      if (!raw) return;
      let marker;
      try {
        marker = JSON.parse(raw);
      } catch {
        return;
      }
      if (typeof marker?.chat !== "string" || marker.task !== (task ?? null))
        return;
      const result = await request<{ rows: CommerceReview[] }>(
        `/assistant/commerce-reviews?conversation_id=${encodeURIComponent(marker.chat)}`,
      );
      if (!stillCurrent() || !result.rows.length) return;
      tracked.current = marker.chat;
      set(result.rows);
      return marker.chat as string;
    },
    [set],
  );
  return { rows, tracked, clear, receive, refresh, restore };
}
