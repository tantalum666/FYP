import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  canApproveQuote,
  canReleaseHold,
  changeLines,
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
    quote_version: 1,
    booking_state: "quoted",
    available: true,
    held_covers: false,
    approval_stale: false,
    ticketed: false,
    ticket_receipt: null,
    receipt_covers_quote: false,
    payment_failure: null,
    change: null,
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

test("the panel approves and releases the exact version and does not store the quote", () => {
  assert.match(panel, /usePrivateMutation\(\)/);
  assert.match(panel, /useDraftGuard\(/);
  assert.match(panel, /quote_id: itinerary\.quote_id/);
  assert.match(panel, /quote_version: itinerary\.quote_version/);
  assert.match(panel, /expected_task_version: snapshot\.task_version/);
  assert.match(panel, /\/releases/);
  assert.match(panel, /Release hold/);
  assert.doesNotMatch(panel, /next_step:/);
  assert.doesNotMatch(panel, /(?:sessionStorage|localStorage|indexedDB)\b/);
  assert.match(panel, /No card is charged/);
  assert.match(panel, /desk:tasks/);
  assert.doesNotMatch(panel, /Ticket purchased|Payment complete|Booked successfully/);
});

test("a changed fare shows old and new values and an ended fare cannot be approved", () => {
  const changed = itinerary({
    quote_version: 2,
    approval_stale: true,
    held_covers: false,
    change: {
      reason: "reprice",
      previous_quote_id: "b".repeat(64),
      quote_id: "a".repeat(64),
      fields: [{ name: "total_cents", before: 208000, after: 226000 }],
    },
  });
  assert.deepEqual(changeLines(changed, t), ["Fare: HKD 2080.00 → HKD 2260.00"]);
  assert.match(tripStatus(changed, t), /earlier approval does not cover/);
  assert.equal(canApproveQuote(changed), true);
  assert.equal(canReleaseHold(changed), false);
  const shifted = itinerary({
    quote_version: 2,
    approval_stale: true,
    change: {
      reason: "schedule_change",
      previous_quote_id: "b".repeat(64),
      quote_id: "a".repeat(64),
      fields: [
        { name: "depart_local", before: "2026-12-01T09:00", after: "2026-12-01T11:00" },
        { name: "arrive_local", before: "2026-12-02T14:30", after: "2026-12-02T18:00" },
      ],
    },
  });
  assert.deepEqual(changeLines(shifted, t), [
    "Departs: 2026-12-01T09:00 → 2026-12-01T11:00",
    "Arrives: 2026-12-02T14:30 → 2026-12-02T18:00",
  ]);
  assert.match(tripStatus(shifted, t), /times changed/i);
  const ended = itinerary({
    booking_state: "unavailable",
    available: false,
    approval_stale: true,
    quote_version: 2,
    change: {
      reason: "unavailable",
      previous_quote_id: "a".repeat(64),
      quote_id: null,
      fields: [],
      detail: "The flight was withdrawn.",
    },
  });
  assert.deepEqual(changeLines(ended, t), []);
  assert.match(tripStatus(ended, t), /no longer available/i);
  assert.match(tripStatus(ended, t), /No other fare was offered/);
  assert.equal(canApproveQuote(ended), false);
  assert.equal(canReleaseHold(ended), false);
  assert.equal(canReleaseHold(itinerary({ held_covers: true, booking_state: "held" })), true);
});
