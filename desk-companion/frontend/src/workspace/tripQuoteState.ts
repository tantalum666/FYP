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

export interface TripItinerary {
  terms: TripTerms;
  quote_id: string;
  booking_state: string;
  held_covers: boolean;
  approval_stale: boolean;
  ticketed: boolean;
  ticket_receipt: string | null;
  receipt_covers_quote: boolean;
  payment_failure: string | null;
  live_ticket: boolean;
}

export function formatFare(cents: number, currency: string): string {
  const major = Math.trunc(cents / 100);
  const minor = String(Math.abs(cents % 100)).padStart(2, "0");
  return `${currency} ${major}.${minor}`;
}

/** An approval is offered only while this exact fare is still open. */
export function canApproveQuote(itinerary: TripItinerary): boolean {
  if (itinerary.live_ticket || itinerary.ticketed || itinerary.held_covers) return false;
  return (
    itinerary.booking_state === "quoted" ||
    itinerary.booking_state === "payment_failed" ||
    itinerary.booking_state === "changed"
  );
}

export function tripStatus(
  itinerary: TripItinerary,
  t: (en: string, zh: string) => string,
): string {
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
  if (itinerary.approval_stale) {
    return t(
      "The fare changed. The earlier approval does not cover it.",
      "票价已变化。先前的同意不再覆盖。",
    );
  }
  return t("Not held and not ticketed.", "未保留，也未出票。");
}
