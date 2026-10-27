import { useCallback, useEffect, useRef, useState } from "react";
import { DateTime } from "luxon";
import { request } from "../api";
import { dayISO, occursOn, viewRange } from "../dates";
import type { Session, Snapshot } from "../types";
import { createCalendarReader, readCalendarViews } from "./calendar-reader";

export function usePhoneCalendar(
  session: Session | null | undefined,
  now: DateTime,
  visible: boolean,
) {
  const [date, setDate] = useState(() =>
    dayISO(DateTime.now().setZone("Asia/Hong_Kong")),
  );
  const [month, setMonth] = useState(false);
  const [result, setResult] = useState<{
    plan: Snapshot;
    home: Snapshot;
    planKey: string;
    homeKey: string;
    session: Session;
  }>();
  const [error, setError] = useState<unknown>(null);
  const reader = useRef<ReturnType<typeof createCalendarReader> | null>(null);
  const currentResult = result?.session === session ? result : undefined;
  const zone =
    currentResult?.plan.settings.timezone ??
    session?.settings.timezone ??
    "Asia/Hong_Kong";
  const today = now.setZone(zone).startOf("day");
  const anchor = DateTime.fromISO(date, { zone });
  const range = viewRange(anchor, month ? "month" : "day");
  const planStart = range.start.toUTC().toISO()!,
    planEnd = range.end.toUTC().toISO()!;
  const homeStart = today.toUTC().toISO()!,
    homeEnd = today.plus({ days: 7 }).toUTC().toISO()!;
  const planKey = `${planStart}/${planEnd}`,
    homeKey = `${homeStart}/${homeEnd}`;
  const refresh = useCallback(() => {
    void reader.current?.refresh();
  }, []);
  useEffect(() => {
    if (!session || !visible) return;
    const current = createCalendarReader(
      () =>
        readCalendarViews(
          { start: planStart, end: planEnd },
          { start: homeStart, end: homeEnd },
          (range) =>
            request<Snapshot>(
              `/calendar?start=${encodeURIComponent(range.start)}&end=${encodeURIComponent(range.end)}`,
            ),
        ),
      (value) => {
        setResult({ ...value, planKey, homeKey, session });
        setError(null);
      },
      setError,
    );
    reader.current = current;
    void current.refresh();
    const timer = setInterval(refresh, 15000);
    window.addEventListener("desk:calendar", refresh);
    return () => {
      current.dispose();
      reader.current = null;
      clearInterval(timer);
      window.removeEventListener("desk:calendar", refresh);
    };
  }, [session, visible, planStart, planEnd, homeStart, homeEnd, refresh]);
  const snapshot =
    currentResult?.planKey === planKey ? currentResult.plan : null;
  const homeSnapshot =
    currentResult?.homeKey === homeKey ? currentResult.home : null;
  const daysEvents =
    snapshot?.occurrences
      .filter((e) => occursOn(e, anchor, zone))
      .sort((a, b) => a.start.localeCompare(b.start)) ?? null;
  const next = homeSnapshot?.occurrences
    .filter((e) => !e.completed && DateTime.fromISO(e.end) > now)
    .sort((a, b) => a.start.localeCompare(b.start))[0];
  return {
    date,
    setDate,
    month,
    setMonth,
    zone,
    today,
    todayKey: dayISO(today),
    anchor,
    snapshot,
    homeSnapshot,
    daysEvents,
    next,
    error,
    refresh,
  };
}
