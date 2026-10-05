import { DateTime } from "luxon";
import type { Occurrence } from "../types";

export function lunarDate(day: DateTime, language: "en" | "zh", short = false) {
  try {
    return new Intl.DateTimeFormat(
      language === "zh" ? "zh-Hans-u-ca-chinese" : "en-u-ca-chinese",
      {
        timeZone: day.zoneName!,
        month: short ? undefined : "long",
        day: "numeric",
      },
    ).format(day.set({ hour: 12 }).toJSDate());
  } catch {
    return "";
  }
}

export function busyMinutes(events: Occurrence[], day: DateTime) {
  const start = day.startOf("day").toMillis(),
    end = day.startOf("day").plus({ days: 1 }).toMillis();
  const ranges = events
    .filter((e) => e.busy && !e.completed)
    .map((e) => [
      Math.max(start, DateTime.fromISO(e.start).toMillis()),
      Math.min(end, DateTime.fromISO(e.end).toMillis()),
    ])
    .filter(([a, b]) => b > a)
    .sort((a, b) => a[0] - b[0]);
  let total = 0,
    previousEnd = start;
  for (const [a, b] of ranges) {
    total += Math.max(0, b - Math.max(a, previousEnd));
    previousEnd = Math.max(previousEnd, b);
  }
  return Math.round(total / 60000);
}
