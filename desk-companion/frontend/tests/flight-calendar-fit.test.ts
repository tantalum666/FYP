import assert from "node:assert/strict";
import test from "node:test";
import {
  calendarFitLabel,
  flightStatus,
  optionTime,
  type SandboxFlight,
} from "../src/workspace/commercePresentation.ts";
const zh = (en: string, cn: string) => cn;
const leg = {
  flight: "BA6631",
  origin: "HKG",
  destination: "HND",
  departs: "2026-11-29T18:30",
  arrives: "2026-11-30T02:55",
};
test("the comparison is short and day changes remain explicit in both directions", () => {
  assert.equal(optionTime(leg, zh), "18:30–02:55 次日");
  assert.equal(
    optionTime(
      { ...leg, departs: "2026-12-01T01:00", arrives: "2026-11-30T15:00" },
      zh,
    ),
    "01:00–15:00 前一日",
  );
  assert.equal(calendarFitLabel("unknown", zh), "日程匹配待核实");
});
test("a calendar change is visible on the compact home as well as the price review", () => {
  const quote: SandboxFlight = {
    id: "f",
    version: 1,
    state: "quoted",
    segments: [leg],
    currency: "HKD",
    adults: 1,
    quoted_minor: 4700,
    review_minor: 4700,
    previous_minor: null,
    approved_minor: null,
    review_deadline_ms: null,
    charged_minor: null,
    pnr: null,
    released: false,
  };
  assert.equal(flightStatus(quote, zh), "BA6631 · HK$47.00");
  assert.match(
    flightStatus({ ...quote, calendar_fit: "conflict" }, zh),
    /和桌面日程冲突/,
  );
  assert.match(
    flightStatus({ ...quote, calendar_fit: "unknown" }, zh),
    /待核实/,
  );
});
