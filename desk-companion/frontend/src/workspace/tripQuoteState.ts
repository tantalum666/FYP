export interface TripTerms {
  origin: string;
  destination: string;
  depart_local: string;
  arrive_local: string;
  timezone: string;
  arrive_timezone: string;
  passengers: number;
  baggage_kg: number;
  total_cents: number;
  currency: string;
  fare_rules: string;
}

export interface TripFieldChange {
  name: string;
  before: string | number;
  after: string | number;
}

export interface TripChange {
  reason: string;
  previous_quote_id: string;
  quote_id: string | null;
  fields: TripFieldChange[];
  detail?: string;
}

export interface TripItinerary {
  terms: TripTerms;
  quote_id: string;
  quote_version: number;
  booking_state: string;
  available: boolean;
  held_covers: boolean;
  approval_stale: boolean;
  ticketed: boolean;
  ticket_receipt: string | null;
  receipt_covers_quote: boolean;
  payment_failure: string | null;
  change: TripChange | null;
  live_ticket: boolean;
}

const FIELD_LABELS: Record<string, [string, string]> = {
  total_cents: ["Fare", "票价"],
  depart_local: ["Departs", "出发"],
  arrive_local: ["Arrives", "到达"],
  timezone: ["Departure timezone", "出发时区"],
  arrive_timezone: ["Arrival timezone", "到达时区"],
  origin: ["From", "出发机场"],
  destination: ["To", "到达机场"],
  passengers: ["Passengers", "乘客"],
  baggage_kg: ["Baggage kg", "行李公斤"],
  fare_rules: ["Fare rules", "票价规则"],
};

export function formatFare(cents: number, currency: string): string {
  const major = Math.trunc(cents / 100);
  const minor = String(Math.abs(cents % 100)).padStart(2, "0");
  return `${currency} ${major}.${minor}`;
}

function fieldValue(name: string, value: string | number, currency: string): string {
  if (name === "total_cents") return formatFare(Number(value), currency);
  return String(value);
}

/** Old and new values for the fields the fixture actually changed. */
export function changeLines(
  itinerary: TripItinerary,
  t: (en: string, zh: string) => string,
): string[] {
  const change = itinerary.change;
  if (!change || change.reason === "unavailable") return [];
  return change.fields.map((field) => {
    const label = FIELD_LABELS[field.name] ?? [field.name, field.name];
    const before = fieldValue(field.name, field.before, itinerary.terms.currency);
    const after = fieldValue(field.name, field.after, itinerary.terms.currency);
    return `${t(label[0], label[1])}: ${before} → ${after}`;
  });
}

/** An approval is offered only while this exact fare is still open. */
export function canApproveQuote(itinerary: TripItinerary): boolean {
  if (itinerary.live_ticket || itinerary.ticketed || itinerary.held_covers) return false;
  if (itinerary.available === false || itinerary.booking_state === "unavailable") return false;
  return (
    itinerary.booking_state === "quoted" ||
    itinerary.booking_state === "payment_failed" ||
    itinerary.booking_state === "changed"
  );
}

/** A release is offered only while this exact version is the current hold. */
export function canReleaseHold(itinerary: TripItinerary): boolean {
  return itinerary.held_covers === true && itinerary.live_ticket === false;
}

export function tripStatus(
  itinerary: TripItinerary,
  t: (en: string, zh: string) => string,
): string {
  if (itinerary.booking_state === "unavailable" || itinerary.available === false) {
    return t(
      "This fare is no longer available. No other fare was offered.",
      "这份票价已经结束。没有另找替代。",
    );
  }
  if (itinerary.ticketed) {
    return t(
      `Fixture receipt ${itinerary.ticket_receipt} recorded. No live ticket was bought.`,
      `已记下夹具回执 ${itinerary.ticket_receipt}。没有购买真实机票。`,
    );
  }
  if (itinerary.booking_state === "changed") {
    return t(
      "The itinerary changed. The earlier receipt does not cover this fare.",
      "行程已变化。先前的回执不覆盖这份票价。",
    );
  }
  if (itinerary.booking_state === "payment_failed") {
    return t(
      "Payment failed. This trip is not ticketed.",
      "付款失败。这次行程没有出票。",
    );
  }
  if (itinerary.held_covers) {
    return t("Held. Not paid and not ticketed.", "已保留。未付款，也未出票。");
  }
  if (itinerary.approval_stale && itinerary.change?.reason === "schedule_change") {
    return t(
      "The times changed. The earlier approval does not cover them.",
      "时间已变化。先前的同意不再覆盖。",
    );
  }
  if (itinerary.approval_stale) {
    return t(
      "The fare changed. The earlier approval does not cover it.",
      "票价已变化。先前的同意不再覆盖。",
    );
  }
  return t("Not held and not ticketed.", "未保留，也未出票。");
}
