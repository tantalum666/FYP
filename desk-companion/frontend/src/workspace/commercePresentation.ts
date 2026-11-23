import type { Translate } from "../types";

interface ShopIdentity {
  product_id: number;
  sku: string;
  quantity: number;
}
interface ShopLine extends ShopIdentity {
  subtotal_minor: number;
  discount_minor: number;
  subtotal_tax_minor: number;
  tax_minor: number;
}
interface ShopTotals {
  currency: "HKD";
  subtotal_minor: number;
  discount_minor: number;
  shipping_minor: number;
  tax_minor: number;
  fees_minor: number;
  total_minor: number;
  rate_id: string;
}
type ShopQuote = {
  shipping_name: string;
  destination: string | null;
} & (
  | { name: string; unit_minor: number; terms: ShopTotals & ShopIdentity }
  | {
      item_names: Record<string, string>;
      terms: ShopTotals & {
        items: ShopLine[];
        fees: { name: string; total_minor: number; tax_minor: number }[];
        shipping_tax_minor: number;
      };
    }
);
export type SandboxShop = {
  id: string;
  version: number;
  state: string;
  previous: ShopQuote | null;
  approved_minor: number | null;
  unavailable_product?: string;
  unavailable_reason?: string;
  can_search_again?: boolean;
  alternatives?: { number: number; name: string; sku: string; quantity: number; shipping_minor: number; total_minor: number }[];
  checkout_change?: { removed: string[]; added: string[]; total_minor: number };
  cancel_unavailable?: boolean;
  receipt: {
    order: number;
    order_status: string;
    charged_minor: number;
    test_mode: boolean;
    can_cancel?: boolean;
    buyer_cancel_requested?: boolean;
    refunded_minor?: number | null;
    net_minor?: number | null;
    pending_minor?: number | null;
    last_verified?: boolean;
  } | null;
} & ({ quote: ShopQuote; review_minor: number } | { quote: null; review_minor: null });

export type CalendarFit = "clear" | "conflict" | "unknown";
export function calendarFitLabel(fit: CalendarFit, t: Translate) {
  if (fit === "clear") return t("Fits desk calendar", "已错开桌面日程");
  if (fit === "conflict") return t("Overlaps desk calendar", "和桌面日程冲突");
  return t("Calendar match unverified", "日程匹配待核实");
}

export interface SandboxFlight {
  calendar_linked?: boolean;
  calendar_preview?: {
    fit?: CalendarFit;
    title: string;
    start_local: string;
    end_local: string;
    timezone: string;
  };
  calendar_fit?: CalendarFit;
  can_find_other?: boolean;
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
  review_deadline_ms: number | null;
  charged_minor: number | null;
  pnr: string | null;
  released: boolean;
  stop_status?: string | null;
}

export type CommerceReview =
  ((SandboxShop & { kind: "shop" }) | (SandboxFlight & { kind: "flight" })) &
  { quiet_update?: boolean };
export type CommerceRef = {
  id: string;
  version: number;
  amount_minor: number | null;
  kind: CommerceReview["kind"];
};
export type StatusMark = Pick<
  CommerceReview,
  "id" | "kind" | "version" | "state"
>;
export const orderKey = (row: Pick<StatusMark, "kind" | "id">) =>
  row.kind + "/" + row.id;
export const hkd = (minor: number) => `HK$${(minor / 100).toFixed(2)}`;
export const needsDecision = (row: { state: string }) =>
  ["choosing", "quoted", "reprice", "submit_unknown", "retry"].includes(row.state);
export const needsOwnerReview = (row: CommerceReview) =>
  needsDecision(row) ||
  row.state === "refund_retry" ||
  (row.kind === "flight" && !!row.calendar_preview);
export const reviewRef = (
  row: Pick<CommerceReview, "id" | "version" | "review_minor">,
  kind: CommerceReview["kind"],
): CommerceRef => ({
  id: row.id,
  version: row.version,
  amount_minor: row.review_minor,
  kind,
});

export function typedReviewRef(rows: CommerceReview[], hasFlightShortlist: boolean) {
  const pending = rows.filter(needsDecision);
  if (pending.length !== 1) return undefined;
  const [row] = pending;
  // Both open lists accept a bare ordinal. Only a deliberate card choice distinguishes them.
  if (hasFlightShortlist && row.kind === "shop" && row.state === "choosing") return undefined;
  return reviewRef(row, row.kind);
}

type Leg = SandboxFlight["segments"][number];
export type CalendarFlightChoice = {
  origin: string;
  destination: string;
  departure: string;
  flight_number: string;
  nonstop: true;
  avoid_calendar_conflicts: true;
  max_hkd?: number;
  airline?: string;
  rehearse_price_change?: boolean;
};
export type FlightAlternatives = {
  shortlist_number?: number;
  original?: boolean;
  unavailable_flight: string;
  avoid_calendar_conflicts?: boolean;
  requested_calendar_fit?: "conflict" | "unknown";
  max_minor?: number | null;
  alternatives: {
    segment: Leg;
    total_minor: number;
    calendar_choice?: CalendarFlightChoice;
  }[];
};
export function optionTime(leg: Leg, t: Translate) {
  const [day, from] = leg.departs.split("T"),
    [end, to] = leg.arrives.split("T");
  const days =
    (Date.parse(end + "T00:00:00Z") - Date.parse(day + "T00:00:00Z")) /
    86400000;
  const suffix =
    days === 1
      ? t("next day", "次日")
      : days === -1
        ? t("previous day", "前一日")
        : day === end
          ? ""
          : end;
  return `${from}–${to}${suffix ? " " + suffix : ""}`;
}

export function legTime<T extends Pick<Leg, "departs" | "arrives">>(leg: T) {
  const [day, from] = leg.departs.split("T"),
    [end, to] = leg.arrives.split("T");
  return `${day} · ${from}–${end === day ? "" : end + " "}${to}`;
}

const shopStates: Record<string, [string, string]> = {
  submitting: ["Placing test order", "正在提交测试单"],
  checking: ["Checking payment", "正在核对扣款"],
  refund_pending: ["Checking refund", "正在跟进退款"],
  partially_refunded: ["Partially refunded", "已部分退款"],
  refund_review: ["Merchant review needed", "退款待商户核查"],
  refund_retry: ["Cancellation unconfirmed", "撤单尚未确认"],
  retry: ["Payment unconfirmed", "扣款尚未确认"],
  expired: ["Quote expired", "报价已过期"],
  choosing: ["Choose an alternative", "请选择替代商品"],
  unavailable: ["Basket unavailable", "购物清单无法结账"],
  cancelled: ["Cancelled before payment", "已取消，未付款"],
  failed: ["Payment failed", "付款未完成"],
  unverified: ["Payment unverified", "扣款待核实"],
};

export function shopTitle(q: ShopQuote, t: Translate): string {
  if (!("item_names" in q)) return `${q.name} × ${q.terms.quantity}`;
  const lines = q.terms.items;
  if (lines.length === 1)
    return `${q.item_names[lines[0].product_id]} × ${lines[0].quantity}`;
  return t(`${lines.length} products`, `${lines.length} 种商品`);
}

export function shopStatus(row: SandboxShop, t: Translate): string {
  const r = row.receipt,
    item = r ? `#${r.order}` : row.quote ? shopTitle(row.quote, t) : row.unavailable_product;
  if (row.state === "items_changed" && row.checkout_change) {
    const { removed, added, total_minor } = row.checkout_change;
    const delta = [removed, added].map((lines) => lines.join(", ") || t("None", "无")).join(" → ");
    return `${t("Checkout stopped", "结账已停止")} · ${delta} · ${total_minor === row.review_minor ? t("Total still", "总价仍为") : t("New total", "新总价")} ${hkd(total_minor)}`;
  }
  if (row.state === "unavailable" && row.unavailable_reason === "SHOP_OVER_BUDGET")
    return `${item} · ${t("Over the original budget", "超出原预算")}`;
  if (r?.last_verified) return `${item} · ${t("Receipt needs checking", "回执待核实")}`;
  if (row.state === "refunded" && r?.refunded_minor != null)
    return `${item} · ${t("Refunded", "已退款")} ${hkd(r.refunded_minor)}`;
  if (row.cancel_unavailable && row.state === "completed")
    return `${item} · ${t("Cancellation unavailable", "商户未受理撤单")}`;
  if (row.state === "completed" && r)
    return `${item} · ${t("Test charge", "模拟扣款")} ${hkd(r.charged_minor)}`;
  if (row.state === "quoted" && row.quote) return `${item} · ${hkd(row.review_minor)}`;
  if (row.state === "reprice" && row.previous && row.quote) {
    if (row.previous.terms.total_minor === row.review_minor)
      return `${item} · ${t("Terms changed", "明细已变")} · ${hkd(row.review_minor)}`;
    return `${item} · ${hkd(row.previous.terms.total_minor)} → ${hkd(row.review_minor)}`;
  }
  const label = shopStates[row.state] ?? ["Checking order", "正在查单"];
  return `${item} · ${t(label[0], label[1])}`;
}

const flightStates: Record<string, [string, string]> = {
  processing: ["Booking in progress", "正在订票"],
  submitting: ["Submitting booking", "正在提交预订"],
  answering: ["Checking the booking", "正在核对订座"],
  stopped: ["Stopped, hold unverified", "已停止，预授权待核实"],
  stopping: ["Checking stop request", "正在核对停止结果"],
  manual: ["With the supplier", "待供应商人工核查"],
  submit_unknown: ["Submission unconfirmed", "提交结果待核实"],
  cancelled: ["Quote cancelled", "报价已取消"],
  expired: ["Fare expired", "报价已过期"],
  failed: ["Booking failed, charge unconfirmed", "预订失败，扣款待核实"],
  unverified: ["Booking and charge unverified", "订座及扣款待核实"],
};

export function flightStatus(row: SandboxFlight, t: Translate): string {
  const flight = row.segments.map((leg) => leg.flight).join(" / ");
  if (row.calendar_fit && row.calendar_fit !== "clear") {
    const uncertainty =
      row.state === "submit_unknown"
        ? t(" · Original booking unverified", " · 原订座待核实")
        : "";
    return `${flight} · ${calendarFitLabel(row.calendar_fit, t)}${uncertainty}`;
  }
  if (row.state === "reprice" && row.previous_minor != null)
    return `${flight} · ${hkd(row.previous_minor)} → ${hkd(row.review_minor)}`;
  if (row.state === "quoted") return `${flight} · ${hkd(row.review_minor)}`;
  if (row.stop_status === "too_late")
    return `${flight} · ${t("Too late to stop", "已过停止窗口")}`;
  if (row.state === "completed" && row.pnr)
    return `${flight} · ${t("Booking ref", "订座号")} ${row.pnr}`;
  if ((row.state === "stopped" || row.state === "failed") && row.released)
    return `${flight} · ${t("Hold released, no charge", "预授权已释放，未扣款")}`;
  const label = flightStates[row.state] ?? ["Checking booking", "正在查订座"];
  return `${flight} · ${t(label[0], label[1])}`;
}
export const orderStatus = (row: CommerceReview, t: Translate) =>
  row.kind === "shop" ? shopStatus(row, t) : flightStatus(row, t);

const watchStates = new Set([
  "submitting",
  "checking",
  "processing",
  "answering",
  "stopping",
  "refund_pending",
  "reprice",
]);
const importantStates = new Set([
  "reprice",
  "unavailable",
  "items_changed",
  "refunded",
  "partially_refunded",
  "stopped",
  "completed",
  "failed",
  "manual",
  "unverified",
  "refund_review",
  "refund_retry",
  "retry",
  "submit_unknown",
]);
export function watchedMarks(rows: CommerceReview[]): StatusMark[] {
  return rows
    .filter((r) => watchStates.has(r.state))
    .map(({ id, version, state, kind }) => ({ id, version, state, kind }));
}
/** Only newly observed outcomes of work that was already in progress can interrupt a turn. */
export function orderUpdates(
  previous: StatusMark[],
  rows: CommerceReview[],
): CommerceReview[] {
  const seen = new Map(previous.map((row) => [orderKey(row), row]));
  return rows.filter((row) => {
    const old = seen.get(orderKey(row));
    return (
      old &&
      !row.quiet_update &&
      watchStates.has(old.state) &&
      importantStates.has(row.state) &&
      row.version > old.version &&
      (old.state !== row.state || row.state === "reprice")
    );
  });
}
