import type { Translate } from "../types";

interface ShopQuote {
  name: string;
  unit_minor: number;
  shipping_name: string;
  destination: string | null;
  terms: {
    product_id: number;
    sku: string;
    quantity: number;
    currency: "HKD";
    subtotal_minor: number;
    discount_minor: number;
    shipping_minor: number;
    tax_minor: number;
    fees_minor: number;
    total_minor: number;
    rate_id: string;
  };
}
export interface SandboxShop {
  id: string;
  version: number;
  state: string;
  quote: ShopQuote;
  previous: ShopQuote | null;
  review_minor: number;
  approved_minor: number | null;
  cancel_unavailable?: boolean;
  receipt: {
    order: number;
    order_status: string;
    charged_minor: number;
    test_mode: boolean;
    can_cancel?: boolean;
    buyer_cancel_requested?: boolean;
    refunded_minor?: number;
    net_minor?: number;
  } | null;
}

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
  review_deadline_ms: number | null;
  charged_minor: number | null;
  pnr: string | null;
  released: boolean;
  stop_status?: string | null;
}

export type CommerceReview =
  (SandboxShop & { kind: "shop" }) | (SandboxFlight & { kind: "flight" });
export type CommerceRef = {
  id: string;
  version: number;
  amount_minor: number;
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
  ["quoted", "reprice", "submit_unknown", "retry"].includes(row.state);
export const reviewRef = (
  row: Pick<CommerceReview, "id" | "version" | "review_minor">,
  kind: CommerceReview["kind"],
): CommerceRef => ({
  id: row.id,
  version: row.version,
  amount_minor: row.review_minor,
  kind,
});

type Leg = SandboxFlight["segments"][number];
export type FlightAlternatives = {
  unavailable_flight: string;
  max_minor?: number | null;
  alternatives: { segment: Leg; total_minor: number }[];
};
export function legTime(leg: Leg) {
  const [day, from] = leg.departs.split("T"),
    [end, to] = leg.arrives.split("T");
  return `${day} · ${from}–${end === day ? "" : end + " "}${to}`;
}

const shopStates: Record<string, [string, string]> = {
  submitting: ["Placing test order", "正在提交测试单"],
  checking: ["Checking payment", "正在核对扣款"],
  refund_pending: ["Checking refund", "正在跟进退款"],
  refund_review: ["Merchant review needed", "退款待商户核查"],
  refund_retry: ["Cancellation unconfirmed", "撤单尚未确认"],
  retry: ["Payment unconfirmed", "扣款尚未确认"],
  expired: ["Quote expired", "报价已过期"],
  cancelled: ["Cancelled before payment", "已取消，未付款"],
  failed: ["Payment failed", "付款未完成"],
  unverified: ["Payment unverified", "扣款待核实"],
};

export function shopStatus(row: SandboxShop, t: Translate): string {
  const r = row.receipt,
    item = r
      ? `#${r.order}`
      : `${row.quote.name} × ${row.quote.terms.quantity}`;
  if (row.state === "refunded" && r?.refunded_minor != null)
    return `${item} · ${t("Refunded", "已退款")} ${hkd(r.refunded_minor)}`;
  if (row.cancel_unavailable && row.state === "completed")
    return `${item} · ${t("Cancellation unavailable", "商户未受理撤单")}`;
  if (row.state === "completed" && r)
    return `${item} · ${t("Test charge", "模拟扣款")} ${hkd(r.charged_minor)}`;
  if (row.state === "quoted") return `${item} · ${hkd(row.review_minor)}`;
  if (row.state === "reprice" && row.previous)
    return `${item} · ${hkd(row.previous.terms.total_minor)} → ${hkd(row.review_minor)}`;
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
  "refunded",
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
      watchStates.has(old.state) &&
      importantStates.has(row.state) &&
      row.version > old.version &&
      (old.state !== row.state || row.state === "reprice")
    );
  });
}
