import { DateTime } from "luxon";
import type { Language, Occurrence, View } from "./types";

export const locale = (language: Language) =>
  language === "en" ? "en-GB" : "zh-CN";
export const inZone = (iso: string, zone: string) =>
  DateTime.fromISO(iso, { zone });
export const dayISO = (date: DateTime) => date.toISODate()!;
export function monthDays(anchor: DateTime) {
  const start = anchor.startOf("month").startOf("week");
  return Array.from({ length: 42 }, (_, i) => start.plus({ days: i }));
}
export function viewRange(anchor: DateTime, view: View) {
  if (view === "month")
    return {
      start: anchor.startOf("month").startOf("week"),
      end: anchor.endOf("month").endOf("week").plus({ milliseconds: 1 }),
    };
  const start = anchor.startOf(view === "week" ? "week" : "day");
  return {
    start,
    end: start.plus(view === "week" ? { weeks: 1 } : { days: 1 }),
  };
}
export function occursOn(event: Occurrence, date: DateTime, zone: string) {
  return (
    inZone(event.start, zone) < date.plus({ days: 1 }).startOf("day") &&
    inZone(event.end, zone) > date.startOf("day")
  );
}
export function eventTime(event: Occurrence, zone: string, language: Language) {
  if (event.all_day) return language === "en" ? "All day" : "全天";
  return (
    inZone(event.start, zone).toFormat("HH:mm") +
    " – " +
    inZone(event.end, zone).toFormat("HH:mm")
  );
}
export function title(
  event: { title: string; redacted?: boolean },
  language: Language,
) {
  return event.redacted
    ? language === "en"
      ? "Private event"
      : "私人事项"
    : event.title;
}
