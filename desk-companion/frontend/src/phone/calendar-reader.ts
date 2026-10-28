import type { Snapshot } from "../types.ts";

export interface CalendarRange {
  start: string;
  end: string;
}
export type CalendarRead = (range: CalendarRange) => Promise<Snapshot>;

export async function readCalendarViews(
  plan: CalendarRange,
  home: CalendarRange,
  read: CalendarRead,
) {
  const contained =
    Date.parse(plan.start) >= Date.parse(home.start) &&
    Date.parse(plan.end) <= Date.parse(home.end);
  const [homeSnapshot, planSnapshot] = await Promise.all([
    read(home),
    contained ? Promise.resolve(null) : read(plan),
  ]);
  return { home: homeSnapshot, plan: planSnapshot ?? homeSnapshot };
}

/** Coalesce refreshes and never commit a response older than a requested refresh. */
export function createCalendarReader<T>(
  read: () => Promise<T>,
  accept: (value: T) => void,
  reject: (error: unknown) => void,
) {
  let requested = 0;
  let running = false;
  let disposed = false;
  return {
    async refresh() {
      if (disposed) return;
      requested++;
      if (running) return;
      running = true;
      let version: number;
      try {
        do {
          version = requested;
          try {
            const value = await read();
            if (!disposed && version === requested) accept(value);
          } catch (error) {
            if (!disposed && version === requested) reject(error);
          }
        } while (!disposed && version < requested);
      } finally {
        running = false;
      }
    },
    dispose() {
      disposed = true;
    },
  };
}
