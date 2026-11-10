import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  canApproveQuote,
  formatFare,
  tripStatus,
  type TripItinerary,
} from "../src/workspace/tripQuoteState.ts";

const panel = readFileSync(
  new URL("../src/workspace/TripQuotes.tsx", import.meta.url),
  "utf8",
);
const t = (en: string) => en;

function itinerary(overrides: Partial<TripItinerary> = {}): TripItinerary {
  return {
    terms: {
      origin: "HKG",
      destination: "TYO",
      depart_local: "2026-12-01T09:00",
      arrive_local: "2026-12-02T14:30",
      timezone: "Asia/Hong_Kong",
      arrive_timezone: "Asia/Tokyo",
      passengers: 2,
      baggage_kg: 20,
      total_cents: 208000,
      currency: "HKD",
      fare_rules: "Changeable before departure.",
    },
    quote_id: "a".repeat(64),
    booking_state: "quoted",
    held_covers: false,
    approval_stale: false,
    ticketed: false,
    ticket_receipt: null,
    receipt_covers_quote: false,
    payment_failure: null,
    live_ticket: false,
    ...overrides,
  };
}

test("a quote can be approved and a held or ticketed fare cannot", () => {
  assert.equal(canApproveQuote(itinerary()), true);
  assert.equal(canApproveQuote(itinerary({ booking_state: "payment_failed" })), true);
  assert.equal(canApproveQuote(itinerary({ held_covers: true, booking_state: "held" })), false);
  assert.equal(
    canApproveQuote(itinerary({ ticketed: true, booking_state: "ticketed", ticket_receipt: "fix-1" })),
    false,
  );
  assert.equal(canApproveQuote(itinerary({ live_ticket: true })), false);
});

test("payment failure and a fixture receipt are not described as a purchased ticket", () => {
  assert.equal(formatFare(208000, "HKD"), "HKD 2080.00");
  assert.match(tripStatus(itinerary(), t), /Not held and not ticketed/);
  assert.match(
    tripStatus(itinerary({ booking_state: "payment_failed", payment_failure: "Card declined" }), t),
    /Payment failed/,
  );
  assert.doesNotMatch(
    tripStatus(itinerary({ booking_state: "payment_failed" }), t),
    /bought|purchased|ticketed successfully/i,
  );
  const recorded = tripStatus(
    itinerary({ ticketed: true, booking_state: "ticketed", ticket_receipt: "fix-ticket-1" }),
    t,
  );
  assert.match(recorded, /No live ticket was bought/);
  assert.match(
    tripStatus(itinerary({ approval_stale: true, booking_state: "quoted" }), t),
    /earlier approval does not cover/,
  );
});

test("the panel approves with the private mutation and does not store the quote", () => {
  assert.match(panel, /usePrivateMutation\(\)/);
  assert.match(panel, /useDraftGuard\(/);
  assert.match(panel, /quote_id: itinerary\.quote_id/);
  assert.match(panel, /expected_task_version: snapshot\.task_version/);
  assert.doesNotMatch(panel, /next_step:/);
  assert.doesNotMatch(panel, /(?:sessionStorage|localStorage|indexedDB)\b/);
  assert.match(panel, /No card is charged/);
  assert.match(panel, /desk:tasks/);
  assert.doesNotMatch(panel, /Ticket purchased|Payment complete|Booked successfully/);
});
