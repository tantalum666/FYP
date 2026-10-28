import assert from "node:assert/strict";
import test from "node:test";
import { DateTime } from "luxon";
import { eventTime, occursOn, title } from "../src/dates.ts";
import { lunarDate } from "../src/workspace/calendarExtras.ts";

const zone = "Asia/Hong_Kong";
const day = DateTime.fromISO("2026-10-02", { zone });

test("occursOn counts a cross-midnight overlap and excludes an end at local midnight", () => {
  const endsAtMidnight = {
    start: "2026-10-01T15:00:00.000000Z",
    end: "2026-10-01T16:00:00.000000Z",
  };
  const crosses = {
    start: "2026-10-01T15:30:00.000000Z",
    end: "2026-10-01T16:30:00.000000Z",
  };
  assert.equal(occursOn(endsAtMidnight as never, day, zone), false);
  assert.equal(occursOn(endsAtMidnight as never, day.minus({ days: 1 }), zone), true);
  assert.equal(occursOn(crosses as never, day, zone), true);
  assert.equal(occursOn(crosses as never, day.minus({ days: 1 }), zone), true);
});

test("eventTime and title follow the saved language and redaction flag", () => {
  const timed = {
    all_day: false,
    start: "2026-10-02T02:00:00.000000Z",
    end: "2026-10-02T03:30:00.000000Z",
  };
  assert.equal(eventTime({ ...timed, all_day: true } as never, zone, "en"), "All day");
  assert.equal(eventTime({ ...timed, all_day: true } as never, zone, "zh"), "全天");
  assert.equal(eventTime(timed as never, zone, "en"), "10:00 – 11:30");
  assert.equal(title({ title: "Secret", redacted: true }, "en"), "Private event");
  assert.equal(title({ title: "Secret", redacted: true }, "zh"), "私人事项");
  assert.equal(title({ title: "Visible" }, "en"), "Visible");
});

test("short lunar labels omit the month and a broken zone stays blank", () => {
  const full = lunarDate(day, "en", false);
  const short = lunarDate(day, "en", true);
  assert.ok(full.length > 0 && short.length > 0);
  assert.ok(full.length > short.length);
  const broken = DateTime.fromObject(
    { year: 2026, month: 10, day: 2 },
    { zone: "not/a-zone" },
  );
  assert.equal(lunarDate(broken, "en"), "");
});
