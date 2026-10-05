import test from "node:test";
import assert from "node:assert/strict";
import { DateTime } from "luxon";
import {
  appearanceAt,
  calendarDays,
  displayRange,
  mayReturnToDisplay,
  upcomingEvents,
  readAppearance,
} from "../src/device/model.ts";
import type { Occurrence } from "../src/types.ts";
import { monthDays, savedEventPosition, viewRange } from "../src/dates.ts";
import type { EventInput } from "../src/types.ts";

test("saved timed events return to the display's local date, including a date boundary", () => {
  const e = {
    start_local: "2026-09-30T20:00",
    timezone: "America/New_York",
    all_day: false,
  } as EventInput;
  assert.deepEqual(savedEventPosition(e, "Asia/Hong_Kong"), {
    date: "2026-10-01",
    hour: 8,
  });
  assert.deepEqual(
    savedEventPosition({ ...e, all_day: true }, "Asia/Hong_Kong"),
    { date: "2026-09-30", hour: 8 },
  );
});

const event = (
  id: string,
  start: string,
  end: string,
  extra: Partial<Occurrence> = {},
) =>
  ({
    id,
    start,
    end,
    completed: false,
    all_day: false,
    ...extra,
  }) as Occurrence;

test("display appearance follows local hour at the two boundaries", () => {
  assert.equal(appearanceAt("auto", 6), "night");
  assert.equal(appearanceAt("auto", 7), "day");
  assert.equal(appearanceAt("auto", 18), "day");
  assert.equal(appearanceAt("auto", 19), "night");
  assert.equal(appearanceAt("day", 23), "day");
  assert.equal(readAppearance("broken"), "auto");
});
test("five and six week months have complete, bounded grids", () => {
  const september = calendarDays(
    DateTime.fromISO("2026-09-30", { zone: "Asia/Hong_Kong" }),
  );
  assert.equal(september.length, 35);
  assert.equal(september[0].toISODate(), "2026-08-31");
  assert.equal(september.at(-1)?.toISODate(), "2026-10-04");
  const anchor = DateTime.fromISO("2026-09-30", { zone: "Asia/Hong_Kong" });
  const range = viewRange(anchor, "month");
  assert.ok(
    monthDays(anchor).every((day) => day >= range.start && day < range.end),
  );
  const november = calendarDays(
    DateTime.fromISO("2026-11-01", { zone: "Asia/Hong_Kong" }),
  );
  assert.equal(november.length, 42);
  assert.equal(november.at(-1)?.toISODate(), "2026-12-06");
});
test("end of year display includes next month while obeying API range limit", () => {
  for (let month = 1; month <= 12; month++) {
    const now = DateTime.fromObject(
      { year: 2026, month },
      { zone: "Asia/Hong_Kong" },
    ).endOf("month");
    const range = displayRange(now);
    assert.ok(range.end >= now.startOf("day").plus({ days: 15 }));
    assert.ok(range.end.diff(range.start, "days").days <= 62);
    assert.ok(
      calendarDays(now).every((d) => d >= range.start && d < range.end),
    );
  }
});
test("upcoming excludes completed and ended items, keeps an ongoing cross-midnight event", () => {
  const now = DateTime.fromISO("2026-10-01T00:15+08:00");
  const rows = [
    event("future", "2026-10-01T02:00+08:00", "2026-10-01T03:00+08:00"),
    event("done", "2026-10-01T01:00+08:00", "2026-10-01T02:00+08:00", {
      completed: true,
    }),
    event("ended", "2026-09-30T23:00+08:00", "2026-10-01T00:15+08:00"),
    event("ongoing", "2026-09-30T23:50+08:00", "2026-10-01T00:30+08:00"),
  ];
  assert.deepEqual(
    upcomingEvents(rows, now).map((e) => e.id),
    ["ongoing", "future"],
  );
});
test("upcoming ordering compares instants, not written timezone offsets", () => {
  const rows = [
    event("later", "2026-10-01T09:00+08:00", "2026-10-01T10:00+08:00"),
    event("earlier", "2026-10-01T00:30Z", "2026-10-01T01:00Z"),
  ];
  assert.deepEqual(
    upcomingEvents(rows, DateTime.fromISO("2026-10-01T00:00Z")).map(
      (e) => e.id,
    ),
    ["earlier", "later"],
  );
});
test("automatic return never interrupts editing or an unresolved save", () => {
  assert.equal(mayReturnToDisplay(false, false, 59999), false);
  assert.equal(mayReturnToDisplay(false, false, 60000), true);
  assert.equal(mayReturnToDisplay(true, false, 120000), false);
  assert.equal(mayReturnToDisplay(false, true, 120000), false);
});
