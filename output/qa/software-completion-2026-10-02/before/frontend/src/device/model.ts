import { DateTime } from "luxon";
import type { Occurrence } from "../types.ts";

export type Appearance = "auto" | "day" | "night";
export const IDLE_MS = 60_000;

export function appearanceAt(preference: Appearance, hour: number) {
  return preference === "auto"
    ? hour >= 7 && hour < 19
      ? "day"
      : "night"
    : preference;
}

export function displayRange(now: DateTime) {
  const start = now.startOf("month").startOf("week");
  const monthEnd = now.endOf("month").endOf("week").plus({ milliseconds: 1 });
  const horizon = now.startOf("day").plus({ days: 15 });
  return { start, end: monthEnd > horizon ? monthEnd : horizon };
}

export function calendarDays(now: DateTime) {
  const start = now.startOf("month").startOf("week");
  const rows = Math.ceil(
    (now.startOf("month").weekday - 1 + (now.daysInMonth ?? 31)) / 7,
  );
  return Array.from({ length: rows * 7 }, (_, i) => start.plus({ days: i }));
}

export function upcomingEvents(events: Occurrence[], now: DateTime) {
  return events
    .filter(
      (e) =>
        !e.completed && DateTime.fromISO(e.end).toMillis() > now.toMillis(),
    )
    .sort((a, b) => {
      const ongoing = (e: Occurrence) =>
        !e.all_day && DateTime.fromISO(e.start).toMillis() <= now.toMillis();
      if (ongoing(a) !== ongoing(b)) return ongoing(a) ? -1 : 1;
      return (
        DateTime.fromISO(a.start).toMillis() -
          DateTime.fromISO(b.start).toMillis() || a.id.localeCompare(b.id)
      );
    });
}

export function mayReturnToDisplay(
  blocked: boolean,
  pending: boolean,
  elapsed: number,
) {
  return !blocked && !pending && elapsed >= IDLE_MS;
}

export function readAppearance(value: unknown): Appearance {
  return value === "day" || value === "night" ? value : "auto";
}
