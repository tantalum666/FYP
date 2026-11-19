import { useCallback, useRef, useState } from "react";
import { request } from "../api";
import type { Translate } from "../types";

export interface SandboxFlight {
  id: string;
  version: number;
  state: string;
  segments: {
    flight: string;
    origin: string;
    destination: string;
    departs: string;
    arrives: string;
  }[];
  currency: "HKD";
  adults: number;
  quoted_minor: number;
  approved_minor: number | null;
  review_minor: number;
  previous_minor: number | null;
  charged_minor: number | null;
  pnr: string | null;
  released: boolean;
}
export type FlightRef = { id: string; version: number; amount_minor: number };
export const reviewRef = (flight: SandboxFlight): FlightRef => ({
  id: flight.id,
  version: flight.version,
  amount_minor: flight.review_minor,
});
export const needsFlightDecision = (flight: SandboxFlight) =>
  ["quoted", "reprice", "submit_unknown"].includes(flight.state);
const hkd = (minor: number) => `HK$${(minor / 100).toFixed(2)}`;

export function useSandboxFlights() {
  const [rows, setRows] = useState<SandboxFlight[]>([]);
  const tracked = useRef<string | undefined>(undefined);
  const latest = useRef<SandboxFlight[]>([]);
  const set = useCallback((items: SandboxFlight[]) => {
    latest.current = items;
    setRows(items);
  }, []);
  const clear = useCallback(() => {
    tracked.current = undefined;
    sessionStorage.removeItem("desk.flight-review-chat");
    set([]);
  }, [set]);
  const receive = useCallback(
    (chat: string, row: SandboxFlight, task?: string) => {
      sessionStorage.setItem(
        "desk.flight-review-chat",
        JSON.stringify({ chat, task: task ?? null }),
      );
      const other =
        tracked.current === chat
          ? latest.current.filter((x) => x.id !== row.id)
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
      const response = await request<{ bookings: SandboxFlight[] }>(
        `/assistant/flight-bookings?conversation_id=${encodeURIComponent(chat)}`,
      );
      if (tracked.current === chat && previous === latest.current)
        set(response.bookings);
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
      const result = await request<{ bookings: SandboxFlight[] }>(
        `/assistant/flight-bookings?conversation_id=${encodeURIComponent(marker.chat)}`,
      );
      if (!stillCurrent() || !result.bookings.length) return;
      tracked.current = marker.chat;
      set(result.bookings);
      return marker.chat as string;
    },
    [set],
  );
  return { rows, tracked, clear, receive, refresh, restore };
}

export function SandboxFlightCard({
  flight,
  t,
  busy,
  onDecision,
}: {
  flight: SandboxFlight;
  t: Translate;
  busy: boolean;
  onDecision: (text: string, review: FlightRef) => void;
}) {
  const amount = hkd(flight.review_minor);
  const reprice = flight.state === "reprice";
  const retry = flight.state === "submit_unknown";
  const choose = (agree: boolean) => {
    const message = agree
      ? retry
        ? t("Recover this test booking", "恢复原测试单")
        : reprice
          ? t(`Accept new total ${amount}`, `确认新总价 ${amount}`)
          : t(
              `Confirm test booking at ${amount}`,
              `确认按 ${amount} 预订测试航班`,
            )
      : reprice
        ? t("Decline the increase", "拒绝加价")
        : t("Cancel", "取消预订");
    onDecision(message, reviewRef(flight));
  };
  const pending =
    !needsFlightDecision(flight) &&
    ["processing", "submitting", "answering"].includes(flight.state);
  return (
    <section
      className="proposal-card sandbox-flight-card"
      aria-label={t("LetsFG test booking", "LetsFG 测试预订")}
    >
      <strong>{t("LetsFG test booking", "LetsFG 测试预订")}</strong>
      {flight.segments.map((leg, i) => (
        <p key={i}>
          {leg.flight} · {leg.origin} → {leg.destination}
          <br />
          <small>
            {leg.departs.replace("T", " ")} → {leg.arrives.replace("T", " ")}{" "}
            {t("local", "当地时间")}
          </small>
        </p>
      ))}
      {flight.state === "quoted" && (
        <p>
          {t("1 adult · Total", "1 位成人 · 总价")} <strong>{amount}</strong>
        </p>
      )}
      {reprice && (
        <p role="status">
          {t("Price changed", "票价已变")} · {hkd(flight.previous_minor!)} →{" "}
          <strong>{amount}</strong>
        </p>
      )}
      {needsFlightDecision(flight) && (
        <div className="button-row">
          <button type="button" disabled={busy} onClick={() => choose(true)}>
            {retry
              ? t("Recover original order", "恢复原订单")
              : reprice
                ? t(`Accept ${amount}`, `同意新总价 ${amount}`)
                : t(`Book for ${amount}`, `确认预订 ${amount}`)}
          </button>
          {!retry && (
            <button type="button" disabled={busy} onClick={() => choose(false)}>
              {reprice
                ? t("Decline increase", "拒绝加价")
                : t("Cancel", "取消")}
            </button>
          )}
        </div>
      )}
      {pending && (
        <p role="status">
          {t("Checking the original test order…", "正在查回原测试订单…")}
        </p>
      )}
      {flight.state === "completed" && (
        <p role="status">
          {t("Booking reference", "订座编号")} <strong>{flight.pnr}</strong>
          <br />
          {t("Simulated charge", "模拟扣款")}{" "}
          <strong>{hkd(flight.charged_minor!)}</strong> ·{" "}
          {t("Real charge HK$0", "真实扣款 HK$0")}
        </p>
      )}
      {flight.state === "failed" && (
        <p role="status">
          {flight.released
            ? t(
                "Hold released · No charge or reference",
                "预授权已释放 · 无扣款和订座编号",
              )
            : t(
                "Booking failed · No capture verified",
                "预订失败 · 未核实扣款",
              )}
        </p>
      )}
      {flight.state === "unverified" && (
        <p role="alert">
          {t(
            "The booking and charge could not be verified.",
            "订座及扣款尚无法核实。",
          )}
        </p>
      )}
      {flight.state === "expired" && (
        <p>
          {t(
            "Fare expired. Ask for a fresh quote.",
            "报价已过期，请重新查价。",
          )}
        </p>
      )}
      {flight.state === "cancelled" && (
        <p>{t("Quote cancelled", "报价已取消")}</p>
      )}
    </section>
  );
}
